// Giant wolf boss: circles the player, claws / bites in reach, charges from afar, leaps back when crowded.

#include "WolfBoss.h"
#include "WolfAnimInstance.h"
#include "StatsComponent.h"
#include "BossHealthBar.h"
#include "MeleeHitComponent.h"
#include "Oss_TermProjectCharacter.h"
#include "Oss_TermProject.h"
#include "AIController.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	TSoftObjectPtr<UAnimSequenceBase> WolfAnim(const TCHAR* Name)
	{
		return TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(FString::Printf(TEXT("/Game/Characters/Wolf/Anims/%s.%s"), Name, Name)));
	}

	bool IsMeleeAttack(EWolfAction Action)
	{
		return Action == EWolfAction::ClawRight || Action == EWolfAction::ClawLeft || Action == EWolfAction::Bite;
	}

	constexpr float CapsuleHalfHeight = 185.f;
}

AWolfBoss::AWolfBoss()
{
	PrimaryActorTick.bCanEverTick = true;

	// the capsule covers the middle of the body (3.7m tall); BodyBlocker covers head to hips
	GetCapsuleComponent()->InitCapsuleSize(120.f, CapsuleHalfHeight);
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);

	BodyBlocker = CreateDefaultSubobject<UBoxComponent>(TEXT("BodyBlocker"));
	BodyBlocker->SetupAttachment(GetCapsuleComponent());
	BodyBlocker->SetBoxExtent(FVector(210.f, 80.f, 70.f));
	BodyBlocker->SetRelativeLocation(FVector(50.f, 0.f, 45.f));
	// hit target only (the player's swings find it by object type): it must NOT block the player,
	// or the player gets wedged under the belly / pushed into it when the wolf turns
	BodyBlocker->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	BodyBlocker->SetCollisionObjectType(ECC_WorldDynamic);
	BodyBlocker->SetCollisionResponseToAllChannels(ECR_Ignore);
	BodyBlocker->SetCanEverAffectNavigation(false);

	// mesh: made in Blender facing -Y (like the mannequin) -> -90 yaw; origin at the feet
	static ConstructorHelpers::FObjectFinder<USkeletalMesh> WolfMesh(TEXT("/Game/Characters/Wolf/SK_Wolf.SK_Wolf"));
	if (WolfMesh.Succeeded())
	{
		GetMesh()->SetSkeletalMeshAsset(WolfMesh.Object);
	}
	GetMesh()->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -CapsuleHalfHeight), FRotator(0.f, -90.f, 0.f));
	GetMesh()->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);

	// AI-driven, rotation handled here (never toward the movement)
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	AIControllerClass = AAIController::StaticClass();
	bUseControllerRotationYaw = false;
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->bOrientRotationToMovement = false;
	Movement->bUseControllerDesiredRotation = false;
	Movement->MaxWalkSpeed = WalkSpeed;

	Stats = CreateDefaultSubobject<UStatsComponent>(TEXT("Stats"));
	MeleeHit = CreateDefaultSubobject<UMeleeHitComponent>(TEXT("MeleeHit"));
	MeleeHit->IgnoreTags.Add(TEXT("Enemy"));

	WalkForwardAnim = WolfAnim(TEXT("Wolf_Walk_Fwd"));
	WalkLeftAnim = WolfAnim(TEXT("Wolf_Walk_Left"));
	WalkRightAnim = WolfAnim(TEXT("Wolf_Walk_Right"));
	TurnLeftAnim = WolfAnim(TEXT("Wolf_Turn_Left_45"));
	TurnRightAnim = WolfAnim(TEXT("Wolf_Turn_Right_45"));
	ClawRightAnim = WolfAnim(TEXT("Wolf_Claw_Right"));
	ClawLeftAnim = WolfAnim(TEXT("Wolf_Claw_Left"));
	BiteAnim = WolfAnim(TEXT("Wolf_Bite"));
	ChargeAnim = WolfAnim(TEXT("Wolf_Charge"));
	JumpBackAnim = WolfAnim(TEXT("Wolf_Jump_Back"));

	Tags.Add(TEXT("LockOnTarget"));
	Tags.Add(TEXT("Enemy"));
}

void AWolfBoss::BeginPlay()
{
	Super::BeginPlay();

	if (UClass* Class = AnimClass.LoadSynchronous())
	{
		GetMesh()->SetAnimInstanceClass(Class);
	}
	else
	{
		UE_LOG(LogOss_TermProject, Warning, TEXT("'%s': anim blueprint %s not found - create ABP_Wolf (Slot 'DefaultSlot' -> Output Pose)"), *GetNameSafe(this), *AnimClass.ToString());
		if (GEngine)
		{
			GEngine->AddOnScreenDebugMessage(-1, 10.f, FColor::Red, TEXT("WolfBoss: ABP_Wolf missing (Content/Characters/Wolf)"));
		}
	}

	for (TSoftObjectPtr<UAnimSequenceBase>* Anim : { &WalkForwardAnim, &WalkLeftAnim, &WalkRightAnim, &TurnLeftAnim, &TurnRightAnim,
		&ClawRightAnim, &ClawLeftAnim, &BiteAnim, &ChargeAnim, &JumpBackAnim })
	{
		Anim->LoadSynchronous();
	}

	// also at runtime, so instances placed before this change don't keep blocking the player
	BodyBlocker->SetCollisionResponseToAllChannels(ECR_Ignore);

	HomeTransform = GetActorTransform();
	Stats->SetMaxHealth(BossHealth);
	Stats->RestoreAll();
	Stats->OnDeath.AddDynamic(this, &AWolfBoss::HandleDeath);
	MeleeHit->bDebugDraw = bDebugHits;
}

void AWolfBoss::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	ShowHealthBar(false);
	Super::EndPlay(EndPlayReason);
}

// ---------------------------------------------------------------- helpers

APawn* AWolfBoss::GetPlayer() const
{
	APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!Player || !Player->CanBeDamaged())
	{
		return nullptr;
	}
	if (const AOss_TermProjectCharacter* PlayerCharacter = Cast<AOss_TermProjectCharacter>(Player))
	{
		if ((PlayerCharacter->GetStats() && PlayerCharacter->GetStats()->IsDead()) || PlayerCharacter->IsResting())
		{
			return nullptr;
		}
	}
	return Player;
}

void AWolfBoss::GetPlayerOffset(const APawn* Player, float& OutDistance, float& OutYaw) const
{
	const FVector Local = GetActorTransform().InverseTransformPositionNoScale(Player->GetActorLocation());
	OutDistance = FVector2D(Local.X, Local.Y).Size();
	OutYaw = FMath::RadiansToDegrees(FMath::Atan2(Local.Y, Local.X));
}

void AWolfBoss::FaceTowards(const FVector& Location, float DeltaSeconds, float DegreesPerSecond)
{
	FVector Dir = Location - GetActorLocation();
	Dir.Z = 0.f;
	if (!Dir.IsNearlyZero())
	{
		SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(), Dir.Rotation(), DeltaSeconds, DegreesPerSecond));
	}
}

float AWolfBoss::PlayAnim(const TSoftObjectPtr<UAnimSequenceBase>& Anim, float Rate, int32 Loops, float BlendIn, float BlendOut)
{
	UAnimSequenceBase* Sequence = Anim.Get();
	UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance();
	if (!Sequence || !AnimInstance || !AnimInstance->PlaySlotAnimationAsDynamicMontage(Sequence, SlotName, BlendIn, BlendOut, Rate, Loops))
	{
		return 0.f;
	}
	return Sequence->GetPlayLength() / FMath::Max(Rate, 0.05f);
}

void AWolfBoss::SetLoop(const TSoftObjectPtr<UAnimSequenceBase>& Anim)
{
	if (CurrentLoop && CurrentLoop == Anim.Get())
	{
		return;
	}
	CurrentLoop = Anim.Get();
	PlayAnim(Anim, 1.f, 100000, 0.25f, 0.25f);
}

void AWolfBoss::StopLoop()
{
	if (CurrentLoop)
	{
		CurrentLoop = nullptr;
		if (UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance())
		{
			AnimInstance->StopSlotAnimation(0.25f, SlotName);
		}
	}
}

// ---------------------------------------------------------------- AI

void AWolfBoss::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	if (State == EWolfState::Dead)
	{
		return;
	}

	APawn* Player = GetPlayer();
	const float Now = GetWorld()->GetTimeSeconds();

	UpdateHeadLook(Player, DeltaSeconds);

	if (State == EWolfState::Dormant)
	{
		if (Player)
		{
			float Distance, Yaw;
			GetPlayerOffset(Player, Distance, Yaw);
			FHitResult Hit;
			FCollisionQueryParams Params(SCENE_QUERY_STAT(WolfSight), false, this);
			const bool bVisible = !GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation() + FVector(0.f, 0.f, 120.f), Player->GetActorLocation(), ECC_Visibility, Params) || Hit.GetActor() == Player;
			if (Distance <= AggroRange && bVisible)
			{
				Engage();
			}
		}
		return;
	}

	// player gone (dead / resting): stop and wait
	if (!Player)
	{
		if (State == EWolfState::Approach || State == EWolfState::Strafe)
		{
			StopLoop();
			EnterRecover();
		}
		return;
	}

	float Distance, Yaw;
	GetPlayerOffset(Player, Distance, Yaw);
	UCharacterMovementComponent* Movement = GetCharacterMovement();

	switch (State)
	{
	case EWolfState::Recover:
		// always keep the player in front
		FaceTowards(Player->GetActorLocation(), DeltaSeconds, bPhaseTwo ? 130.f : 90.f);
		if (Now >= StateEndTime)
		{
			Decide();
		}
		break;

	case EWolfState::Action:
	{
		// attacks keep tracking the player during the wind-up, then commit (so they can be dodged)
		FTimerManager& Timers = GetWorldTimerManager();
		const float Total = Timers.GetTimerRate(ActionEndTimer) + 0.2f;
		const float Elapsed = Timers.GetTimerElapsed(ActionEndTimer);
		if (Total > 0.f && Elapsed >= 0.f)
		{
			const float Fraction = Elapsed / Total;
			if (IsMeleeAttack(CurrentAction) && Fraction < 0.22f)
			{
				FaceTowards(Player->GetActorLocation(), DeltaSeconds, bPhaseTwo ? 220.f : 160.f);
			}
			else if (CurrentAction == EWolfAction::Charge && Fraction < 0.15f)
			{
				FaceTowards(Player->GetActorLocation(), DeltaSeconds, 140.f);
			}
		}
		break;
	}

	case EWolfState::Approach:
		Movement->MaxWalkSpeed = WalkSpeed;
		FaceTowards(Player->GetActorLocation(), DeltaSeconds, 80.f);
		AddMovementInput(GetActorForwardVector());
		if (Distance <= AttackRange - 40.f || Now >= StateEndTime || FMath::Abs(Yaw) > TurnAngle)
		{
			Decide();
		}
		break;

	case EWolfState::Strafe:
		Movement->MaxWalkSpeed = StrafeSpeed;
		FaceTowards(Player->GetActorLocation(), DeltaSeconds, 90.f);
		AddMovementInput(GetActorRightVector() * StrafeDirection);
		if (Now >= StateEndTime || Distance < TooCloseRange || Distance > 1500.f)
		{
			Decide();
		}
		break;

	default:
		break;
	}
}

void AWolfBoss::UpdateHeadLook(APawn* Player, float DeltaSeconds)
{
	// target: the player's direction relative to the body, clamped; straight ahead when there's nothing to look at
	// or while the head is busy (the bite aims the head itself, the charge looks where it runs)
	UWolfAnimInstance* WolfAnim = Cast<UWolfAnimInstance>(GetMesh()->GetAnimInstance());
	if (!WolfAnim)
	{
		return;
	}

	// measured from the base of the neck (the pivot), not the body's center: up close the player is
	// beside / under the head even when they're "in front" of the body, and far below the 3m-high head
	constexpr float RestSnoutPitch = 15.f;		// at rest the snout points ~15 deg above level from the neck base
	constexpr float MaxPitchDown = 50.f;
	constexpr float MaxPitchUp = 15.f;

	float TargetYaw = 0.f;
	float TargetPitch = 0.f;
	if (Player && CurrentAction != EWolfAction::Bite && CurrentAction != EWolfAction::Charge)
	{
		float Distance, BodyYaw;
		GetPlayerOffset(Player, Distance, BodyYaw);
		if (State != EWolfState::Dormant || Distance <= AggroRange)
		{
			const FVector NeckBase = GetMesh()->GetSocketLocation(TEXT("neck_01"));
			const FVector Aim = Player->GetActorLocation() + FVector(0.f, 0.f, 30.f);	// chest height
			const FVector Local = GetActorTransform().InverseTransformVectorNoScale(Aim - NeckBase);
			const float Horizontal = FVector2D(Local.X, Local.Y).Size();

			TargetYaw = FMath::Clamp(FMath::RadiansToDegrees(FMath::Atan2(Local.Y, Local.X)), -MaxHeadYaw, MaxHeadYaw);
			TargetPitch = FMath::Clamp(FMath::RadiansToDegrees(FMath::Atan2(Local.Z, Horizontal)) - RestSnoutPitch, -MaxPitchDown, MaxPitchUp);
		}
	}

	HeadYaw = FMath::FInterpTo(HeadYaw, TargetYaw, DeltaSeconds, HeadTurnSpeed);
	// pitch lives in the anim instance (Roll = nod about the mesh's side axis; + = nose down)
	const float HeadPitch = FMath::FInterpTo(-WolfAnim->HeadLookRotation.Roll, TargetPitch, DeltaSeconds, HeadTurnSpeed);

	// mesh component space: the wolf faces +Y, so yaw turns it about Z (+ = its right) and roll nods it about X
	WolfAnim->HeadLookRotation = FRotator(0.f, HeadYaw, -HeadPitch);
}

void AWolfBoss::Engage()
{
	ShowHealthBar(true);
	NextChargeTime = GetWorld()->GetTimeSeconds() + 2.f;
	Decide();
}

EWolfAction AWolfBoss::PickMeleeAttack(float PlayerYaw)
{
	// the claw that starts on the player's side; bite straight ahead
	EWolfAction Pick;
	const float Roll = FMath::FRand();
	if (Roll < 0.38f)
	{
		Pick = EWolfAction::Bite;
	}
	else
	{
		const bool bRight = (PlayerYaw > 10.f) ? (FMath::FRand() < 0.8f) : (PlayerYaw < -10.f ? (FMath::FRand() < 0.2f) : FMath::RandBool());
		Pick = bRight ? EWolfAction::ClawRight : EWolfAction::ClawLeft;
	}

	// no third repeat in a row
	if (Pick == LastAttack && SameAttackCount >= 2)
	{
		Pick = (Pick == EWolfAction::Bite) ? (FMath::RandBool() ? EWolfAction::ClawRight : EWolfAction::ClawLeft) : EWolfAction::Bite;
	}
	return Pick;
}

void AWolfBoss::Decide()
{
	if (State == EWolfState::Dead)
	{
		return;
	}

	if (QueuedAction != EWolfAction::None)
	{
		const EWolfAction Next = QueuedAction;
		QueuedAction = EWolfAction::None;
		StartAction(Next);
		return;
	}

	APawn* Player = GetPlayer();
	if (!Player)
	{
		StopLoop();
		EnterRecover();
		return;
	}

	float Distance, Yaw;
	GetPlayerOffset(Player, Distance, Yaw);
	const float Now = GetWorld()->GetTimeSeconds();
	const float Roll = FMath::FRand();

	if (FMath::Abs(Yaw) > TurnAngle)
	{
		StartAction(Yaw > 0.f ? EWolfAction::TurnRight : EWolfAction::TurnLeft);
	}
	else if (Distance < TooCloseRange)
	{
		// mostly fights back up close; leaps away only now and then
		const bool bLeap = Now >= NextJumpBackTime && Roll < JumpBackChance;
		StartAction(bLeap ? EWolfAction::JumpBack : PickMeleeAttack(Yaw));
	}
	else if (Distance <= AttackRange)
	{
		StartAction(PickMeleeAttack(Yaw));
	}
	else
	{
		const bool bCanCharge = Distance >= MinChargeRange && Now >= NextChargeTime;
		const float ChargeChance = Distance > 1300.f ? 0.6f : 0.4f;
		if (bCanCharge && Roll < ChargeChance)
		{
			StartAction(EWolfAction::Charge);
		}
		else if (Distance <= 1300.f && Roll < ChargeChance + 0.3f)
		{
			// circle the player for a moment
			State = EWolfState::Strafe;
			CurrentAction = EWolfAction::None;
			StrafeDirection = FMath::RandBool() ? 1.f : -1.f;
			StateEndTime = Now + FMath::FRandRange(1.8f, 3.2f);
			SetLoop(StrafeDirection > 0.f ? WalkRightAnim : WalkLeftAnim);
		}
		else
		{
			State = EWolfState::Approach;
			CurrentAction = EWolfAction::None;
			StateEndTime = Now + 5.f;
			SetLoop(WalkForwardAnim);
		}
	}
}

void AWolfBoss::StartAction(EWolfAction Action)
{
	const TSoftObjectPtr<UAnimSequenceBase>* Anim = nullptr;
	switch (Action)
	{
	case EWolfAction::ClawRight:	Anim = &ClawRightAnim; break;
	case EWolfAction::ClawLeft:		Anim = &ClawLeftAnim; break;
	case EWolfAction::Bite:			Anim = &BiteAnim; break;
	case EWolfAction::Charge:		Anim = &ChargeAnim; break;
	case EWolfAction::JumpBack:		Anim = &JumpBackAnim; break;
	case EWolfAction::TurnLeft:		Anim = &TurnLeftAnim; break;
	case EWolfAction::TurnRight:	Anim = &TurnRightAnim; break;
	default:						break;
	}
	if (!Anim)
	{
		EnterRecover();
		return;
	}

	// attacks square up to the player first (the turn animations handle big angles)
	APawn* Player = GetPlayer();
	if (Player && (IsMeleeAttack(Action) || Action == EWolfAction::Charge))
	{
		FVector Dir = Player->GetActorLocation() - GetActorLocation();
		Dir.Z = 0.f;
		if (!Dir.IsNearlyZero())
		{
			SetActorRotation(Dir.Rotation());
		}
	}

	CurrentLoop = nullptr;
	GetCharacterMovement()->StopMovementImmediately();
	const float Length = PlayAnim(*Anim, PlayRate(), 1, 0.15f, 0.25f);
	if (Length <= 0.f)
	{
		EnterRecover();
		return;
	}

	State = EWolfState::Action;
	CurrentAction = Action;

	if (IsMeleeAttack(Action))
	{
		SameAttackCount = (Action == LastAttack) ? SameAttackCount + 1 : 1;
		LastAttack = Action;
	}
	if (Action == EWolfAction::Charge)
	{
		NextChargeTime = GetWorld()->GetTimeSeconds() + ChargeCooldown;
	}
	if (Action == EWolfAction::JumpBack)
	{
		NextJumpBackTime = GetWorld()->GetTimeSeconds() + JumpBackCooldown;
	}

	ScheduleHitWindow(Action, Length);
	GetWorldTimerManager().SetTimer(ActionEndTimer, this, &AWolfBoss::EndAction, FMath::Max(Length - 0.2f, 0.1f), false);
}

void AWolfBoss::ScheduleHitWindow(EWolfAction Action, float AnimLength)
{
	FTimerManager& Timers = GetWorldTimerManager();
	Timers.ClearTimer(HitStartTimer);
	Timers.ClearTimer(HitEndTimer);
	MeleeHit->EndHitWindow();

	// bone segments run along the bone (+Y, as exported from Blender)
	auto Shape = [this](const TCHAR* Bone, float Length, float Radius)
	{
		FMeleeHitShape S;
		S.Component = GetMesh();
		S.Socket = Bone;
		S.Start = FVector::ZeroVector;
		S.End = FVector(0.f, Length, 0.f);
		S.Radius = Radius;
		return S;
	};

	TArray<FMeleeHitShape> Shapes;
	FVector2D Window;
	float Damage = 0.f;
	switch (Action)
	{
	case EWolfAction::ClawRight:
	case EWolfAction::ClawLeft:
	{
		const bool bRight = Action == EWolfAction::ClawRight;
		Shapes.Add(Shape(bRight ? TEXT("hand_r") : TEXT("hand_l"), 26.f, 45.f));
		Shapes.Add(Shape(bRight ? TEXT("paw_r") : TEXT("paw_l"), 25.f, 55.f));
		Window = ClawHitWindow;
		Damage = ClawDamage;
		break;
	}
	case EWolfAction::Bite:
		Shapes.Add(Shape(TEXT("head"), 100.f, 55.f));
		Shapes.Add(Shape(TEXT("jaw"), 75.f, 45.f));
		Window = BiteHitWindow;
		Damage = BiteDamage;
		break;
	case EWolfAction::Charge:
		Shapes.Add(Shape(TEXT("head"), 100.f, 80.f));
		Shapes.Add(Shape(TEXT("neck_01"), 50.f, 100.f));
		Shapes.Add(Shape(TEXT("spine_03"), 50.f, 120.f));
		Window = ChargeHitWindow;
		Damage = ChargeDamage;
		break;
	default:
		return;
	}

	MeleeHit->bDebugDraw = bDebugHits;
	Timers.SetTimer(HitStartTimer, FTimerDelegate::CreateWeakLambda(this, [this, Shapes, Damage]()
	{
		MeleeHit->BeginHitWindow(Shapes, Damage);
	}), FMath::Max(AnimLength * Window.X, 0.01f), false);
	Timers.SetTimer(HitEndTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		MeleeHit->EndHitWindow();
	}), FMath::Max(AnimLength * Window.Y, 0.02f), false);
}

void AWolfBoss::EndAction()
{
	FTimerManager& Timers = GetWorldTimerManager();
	Timers.ClearTimer(HitStartTimer);
	Timers.ClearTimer(HitEndTimer);
	MeleeHit->EndHitWindow();

	const EWolfAction Finished = CurrentAction;
	CurrentAction = EWolfAction::None;

	// phase 2 combos: claw into the other claw, leap back into a charge
	if (bPhaseTwo && QueuedAction == EWolfAction::None)
	{
		if (Finished == EWolfAction::ClawRight && FMath::FRand() < 0.5f)
		{
			QueuedAction = EWolfAction::ClawLeft;
		}
		else if (Finished == EWolfAction::ClawLeft && FMath::FRand() < 0.5f)
		{
			QueuedAction = EWolfAction::ClawRight;
		}
		else if (Finished == EWolfAction::JumpBack && FMath::FRand() < 0.6f)
		{
			QueuedAction = EWolfAction::Charge;
		}
	}

	// combos continue right away; after a turn, a short beat to finish facing the player; everything else leaves an opening
	if (QueuedAction != EWolfAction::None)
	{
		Decide();
	}
	else if (Finished == EWolfAction::TurnLeft || Finished == EWolfAction::TurnRight)
	{
		State = EWolfState::Recover;
		StateEndTime = GetWorld()->GetTimeSeconds() + 0.3f;
	}
	else
	{
		EnterRecover();
	}
}

void AWolfBoss::EnterRecover()
{
	State = EWolfState::Recover;
	CurrentAction = EWolfAction::None;
	const float Scale = bPhaseTwo ? PhaseTwoRecoverScale : 1.f;
	StateEndTime = GetWorld()->GetTimeSeconds() + FMath::FRandRange(RecoverTime.X, FMath::Max(RecoverTime.X, RecoverTime.Y)) * Scale;
}

// ---------------------------------------------------------------- damage / death / reset

float AWolfBoss::TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator, AActor* DamageCauser)
{
	const float Damage = Super::TakeDamage(DamageAmount, DamageEvent, EventInstigator, DamageCauser);
	if (Damage <= 0.f || State == EWolfState::Dead)
	{
		return 0.f;
	}

	// a boss doesn't flinch; hitting it wakes it up
	if (State == EWolfState::Dormant)
	{
		Engage();
	}

	const float Taken = Stats->ApplyDamage(Damage, DamageCauser);

	if (!bPhaseTwo && !Stats->IsDead() && Stats->GetHealth() <= Stats->GetMaxHealth() * PhaseTwoHealth)
	{
		bPhaseTwo = true;
		if (GEngine)
		{
			GEngine->AddOnScreenDebugMessage(-1, 3.f, FColor(255, 120, 40), FString::Printf(TEXT("%s is enraged"), *BossName.ToString()), true, FVector2D(2.f, 2.f));
		}
	}
	return Taken;
}

void AWolfBoss::HandleDeath(AActor* DamageCauser)
{
	State = EWolfState::Dead;
	CurrentAction = EWolfAction::None;
	QueuedAction = EWolfAction::None;
	CurrentLoop = nullptr;
	HeadYaw = 0.f;
	if (UWolfAnimInstance* WolfAnim = Cast<UWolfAnimInstance>(GetMesh()->GetAnimInstance()))
	{
		WolfAnim->HeadLookRotation = FRotator::ZeroRotator;
	}

	FTimerManager& Timers = GetWorldTimerManager();
	Timers.ClearTimer(ActionEndTimer);
	Timers.ClearTimer(HitStartTimer);
	Timers.ClearTimer(HitEndTimer);
	MeleeHit->EndHitWindow();
	if (UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance())
	{
		AnimInstance->StopAllMontages(0.2f);
	}

	if (AOss_TermProjectCharacter* Player = Cast<AOss_TermProjectCharacter>(UGameplayStatics::GetPlayerPawn(this, 0)))
	{
		Player->AddSouls(SoulReward);
	}

	ShowHealthBar(false);
	Tags.Remove(TEXT("LockOnTarget"));
	if (AController* AI = GetController())
	{
		AI->UnPossess();
	}

	// collapse (needs SK_Wolf_PhysicsAsset)
	GetCharacterMovement()->DisableMovement();
	GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	BodyBlocker->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	GetMesh()->SetCollisionProfileName(TEXT("Ragdoll"));
	GetMesh()->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	GetMesh()->SetSimulatePhysics(true);

	if (GEngine)
	{
		GEngine->AddOnScreenDebugMessage(-1, 5.f, FColor(255, 210, 90), TEXT("GREAT ENEMY FELLED"), true, FVector2D(3.f, 3.f));
	}
	UE_LOG(LogOss_TermProject, Log, TEXT("'%s' defeated"), *GetNameSafe(this));

	// the body fades away for good (bosses don't come back)
	Timers.SetTimer(CorpseTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		GetMesh()->SetSimulatePhysics(false);
		GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		SetActorHiddenInGame(true);
	}), 8.f, false);
}

void AWolfBoss::ResetBoss()
{
	if (State == EWolfState::Dead)
	{
		return;
	}

	FTimerManager& Timers = GetWorldTimerManager();
	Timers.ClearTimer(ActionEndTimer);
	Timers.ClearTimer(HitStartTimer);
	Timers.ClearTimer(HitEndTimer);
	MeleeHit->EndHitWindow();
	if (UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance())
	{
		AnimInstance->StopAllMontages(0.f);
	}
	CurrentLoop = nullptr;

	TeleportTo(HomeTransform.GetLocation(), HomeTransform.Rotator(), false, true);
	GetCharacterMovement()->StopMovementImmediately();

	Stats->RestoreAll();
	bPhaseTwo = false;
	NextJumpBackTime = 0.f;
	QueuedAction = EWolfAction::None;
	CurrentAction = EWolfAction::None;
	LastAttack = EWolfAction::None;
	SameAttackCount = 0;
	State = EWolfState::Dormant;
	ShowHealthBar(false);
}

// ---------------------------------------------------------------- boss health bar (bottom of the screen)

void AWolfBoss::ShowHealthBar(bool bShow)
{
	if (bShow)
	{
		BossHealthBar::Show(GetWorld(), HealthBar, BossName, Stats);
	}
	else
	{
		BossHealthBar::Hide(GetWorld(), HealthBar);
	}
}
