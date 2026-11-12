// Fishman boss: a 2x scaled mannequin brawler (slam, jump shockwave, foot stomps).

#include "FishmanBoss.h"
#include "StatsComponent.h"
#include "BossHealthBar.h"
#include "MeleeHitComponent.h"
#include "Oss_TermProjectCharacter.h"
#include "Oss_TermProject.h"
#include "AIController.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequenceBase.h"
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
	TSoftObjectPtr<UAnimSequenceBase> FishmanAnim(const TCHAR* Name)
	{
		return TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(FString::Printf(TEXT("/Game/Characters/Fishman/Anims/%s.%s"), Name, Name)));
	}

	// mannequin capsule (the player's size), scaled by BossScale
	constexpr float BaseCapsuleRadius = 42.f;
	constexpr float BaseCapsuleHalfHeight = 96.f;
}

AFishmanBoss::AFishmanBoss()
{
	PrimaryActorTick.bCanEverTick = true;

	GetCapsuleComponent()->InitCapsuleSize(BaseCapsuleRadius * BossScale, BaseCapsuleHalfHeight * BossScale);
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);

	// same mannequin rig as the player, twice the size (replace the mesh in a Blueprint child; keep the mannequin skeleton)
	static ConstructorHelpers::FObjectFinder<USkeletalMesh> MannyMesh(TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple"));
	if (MannyMesh.Succeeded())
	{
		GetMesh()->SetSkeletalMeshAsset(MannyMesh.Object);
	}
	static ConstructorHelpers::FClassFinder<UAnimInstance> UnarmedAnimBP(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed"));
	if (UnarmedAnimBP.Succeeded())
	{
		GetMesh()->SetAnimInstanceClass(UnarmedAnimBP.Class);
	}
	GetMesh()->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -BaseCapsuleHalfHeight * BossScale), FRotator(0.f, -90.f, 0.f));
	GetMesh()->SetRelativeScale3D(FVector(BossScale));
	GetMesh()->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);

	// AI-driven; rotation handled here (always faces the player, never the movement)
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

	SlamAnim = FishmanAnim(TEXT("Fish_Slam"));
	JumpSlamAnim = FishmanAnim(TEXT("Fish_Jump_Slam"));
	StompRightAnim = FishmanAnim(TEXT("Fish_Stomp_R"));
	StompLeftAnim = FishmanAnim(TEXT("Fish_Stomp_L"));

	Tags.Add(TEXT("LockOnTarget"));
	Tags.Add(TEXT("Enemy"));
}

void AFishmanBoss::BeginPlay()
{
	Super::BeginPlay();

	for (TSoftObjectPtr<UAnimSequenceBase>* Anim : { &SlamAnim, &JumpSlamAnim, &StompRightAnim, &StompLeftAnim })
	{
		if (!Anim->LoadSynchronous())
		{
			UE_LOG(LogOss_TermProject, Warning, TEXT("'%s': animation %s not found (import Export/Fish_*.fbx into /Game/Characters/Fishman/Anims)"), *GetNameSafe(this), *Anim->ToString());
		}
	}

	HomeTransform = GetActorTransform();
	GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
	SetLocomotionRate(true);
	Stats->SetMaxHealth(BossHealth);
	Stats->RestoreAll();
	Stats->OnDeath.AddDynamic(this, &AFishmanBoss::HandleDeath);
	MeleeHit->bDebugDraw = bDebugHits;
}

void AFishmanBoss::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	ShowHealthBar(false);
	Super::EndPlay(EndPlayReason);
}

// ---------------------------------------------------------------- helpers

APawn* AFishmanBoss::GetPlayer() const
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

void AFishmanBoss::GetPlayerOffset(const APawn* Player, float& OutDistance, float& OutYaw) const
{
	const FVector Local = GetActorTransform().InverseTransformPositionNoScale(Player->GetActorLocation());
	OutDistance = FVector2D(Local.X, Local.Y).Size();
	OutYaw = FMath::RadiansToDegrees(FMath::Atan2(Local.Y, Local.X));
}

void AFishmanBoss::SetLocomotionRate(bool bLocomotion)
{
	GetMesh()->GlobalAnimRateScale = bLocomotion ? 1.f / FMath::Max(BossScale, 0.1f) : 1.f;
}

void AFishmanBoss::FaceTowards(const FVector& Location, float DeltaSeconds, float DegreesPerSecond)
{
	FVector Dir = Location - GetActorLocation();
	Dir.Z = 0.f;
	if (!Dir.IsNearlyZero())
	{
		SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(), Dir.Rotation(), DeltaSeconds, DegreesPerSecond));
	}
}

// ---------------------------------------------------------------- AI

void AFishmanBoss::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	if (State == EFishmanState::Dead)
	{
		return;
	}

	APawn* Player = GetPlayer();
	const float Now = GetWorld()->GetTimeSeconds();

	if (State == EFishmanState::Dormant)
	{
		if (Player)
		{
			float Distance, Yaw;
			GetPlayerOffset(Player, Distance, Yaw);
			FHitResult Hit;
			FCollisionQueryParams Params(SCENE_QUERY_STAT(FishmanSight), false, this);
			const bool bVisible = !GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation() + FVector(0.f, 0.f, 100.f), Player->GetActorLocation(), ECC_Visibility, Params) || Hit.GetActor() == Player;
			if (Distance <= AggroRange && bVisible)
			{
				Engage();
			}
		}
		return;
	}

	// player gone (dead / resting): stand and wait
	if (!Player)
	{
		if (State == EFishmanState::Approach)
		{
			EnterRecover();
		}
		return;
	}

	float Distance, Yaw;
	GetPlayerOffset(Player, Distance, Yaw);

	switch (State)
	{
	case EFishmanState::Recover:
		FaceTowards(Player->GetActorLocation(), DeltaSeconds, bPhaseTwo ? TurnRate * 1.4f : TurnRate);
		if (Now >= StateEndTime)
		{
			Decide();
		}
		break;

	case EFishmanState::Approach:
		FaceTowards(Player->GetActorLocation(), DeltaSeconds, TurnRate);
		AddMovementInput(GetActorForwardVector());
		if (Distance <= AttackRange - 30.f || Now >= StateEndTime)
		{
			Decide();
		}
		break;

	case EFishmanState::Action:
	{
		// the slam / stomps track the player during the wind-up, then commit (so they can be dodged)
		if (CurrentAction != EFishmanAction::JumpSlam)
		{
			FTimerManager& Timers = GetWorldTimerManager();
			const float Total = Timers.GetTimerRate(ActionEndTimer) + 0.2f;
			const float Elapsed = Timers.GetTimerElapsed(ActionEndTimer);
			if (Total > 0.f && Elapsed >= 0.f && Elapsed / Total < AttackTrackingFraction)
			{
				FaceTowards(Player->GetActorLocation(), DeltaSeconds, bPhaseTwo ? 160.f : 120.f);
			}
		}
		break;
	}

	default:
		break;
	}
}

void AFishmanBoss::Engage()
{
	ShowHealthBar(true);
	Decide();
}

EFishmanAction AFishmanBoss::PickAttack(float Distance, float PlayerYaw)
{
	// beside / behind it and close: jump shockwave (it can't turn fast enough to hit otherwise)
	if (Distance <= CrowdedRange && FMath::Abs(PlayerYaw) > 70.f && LastAttack != EFishmanAction::JumpSlam)
	{
		return EFishmanAction::JumpSlam;
	}

	EFishmanAction Pick;
	const float Roll = FMath::FRand();
	if (Roll < JumpSlamChance)
	{
		Pick = EFishmanAction::JumpSlam;
	}
	else if (Roll < JumpSlamChance + 0.4f)
	{
		Pick = EFishmanAction::Slam;
	}
	else
	{
		// the foot on the player's side
		const bool bRight = (PlayerYaw > 10.f) ? (FMath::FRand() < 0.8f) : (PlayerYaw < -10.f ? (FMath::FRand() < 0.2f) : FMath::RandBool());
		Pick = bRight ? EFishmanAction::StompRight : EFishmanAction::StompLeft;
	}

	// no third repeat in a row, no back-to-back jumps
	if ((Pick == LastAttack && SameAttackCount >= 2) || (Pick == EFishmanAction::JumpSlam && LastAttack == EFishmanAction::JumpSlam))
	{
		Pick = (Pick == EFishmanAction::Slam) ? (PlayerYaw >= 0.f ? EFishmanAction::StompRight : EFishmanAction::StompLeft) : EFishmanAction::Slam;
	}
	return Pick;
}

void AFishmanBoss::Decide()
{
	if (State == EFishmanState::Dead)
	{
		return;
	}

	if (QueuedAction != EFishmanAction::None)
	{
		const EFishmanAction Next = QueuedAction;
		QueuedAction = EFishmanAction::None;
		StartAction(Next);
		return;
	}

	APawn* Player = GetPlayer();
	if (!Player)
	{
		EnterRecover();
		return;
	}

	float Distance, Yaw;
	GetPlayerOffset(Player, Distance, Yaw);

	if (Distance <= CrowdedRange && FMath::Abs(Yaw) > 70.f)
	{
		// player slipped beside / behind: shockwave, or turn to face them first
		if (LastAttack != EFishmanAction::JumpSlam)
		{
			StartAction(EFishmanAction::JumpSlam);
		}
		else
		{
			EnterRecover();
			StateEndTime = GetWorld()->GetTimeSeconds() + 0.4f;
		}
	}
	else if (FMath::Abs(Yaw) > 45.f)
	{
		// turn toward the player before swinging
		EnterRecover();
		StateEndTime = GetWorld()->GetTimeSeconds() + 0.35f;
	}
	else if (Distance <= AttackRange)
	{
		StartAction(PickAttack(Distance, Yaw));
	}
	else
	{
		State = EFishmanState::Approach;
		CurrentAction = EFishmanAction::None;
		StateEndTime = GetWorld()->GetTimeSeconds() + 5.f;
		SetLocomotionRate(true);
	}
}

void AFishmanBoss::StartAction(EFishmanAction Action)
{
	const TSoftObjectPtr<UAnimSequenceBase>* Anim = nullptr;
	switch (Action)
	{
	case EFishmanAction::Slam:			Anim = &SlamAnim; break;
	case EFishmanAction::JumpSlam:		Anim = &JumpSlamAnim; break;
	case EFishmanAction::StompRight:	Anim = &StompRightAnim; break;
	case EFishmanAction::StompLeft:		Anim = &StompLeftAnim; break;
	default:							break;
	}

	UAnimSequenceBase* Sequence = Anim ? Anim->Get() : nullptr;
	UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance();
	if (!Sequence || !AnimInstance)
	{
		EnterRecover();
		return;
	}

	GetCharacterMovement()->StopMovementImmediately();
	SetLocomotionRate(false);
	const float Rate = PlayRate();
	if (!AnimInstance->PlaySlotAnimationAsDynamicMontage(Sequence, SlotName, 0.2f, 0.3f, Rate))
	{
		EnterRecover();
		return;
	}
	const float Length = Sequence->GetPlayLength() / Rate;

	State = EFishmanState::Action;
	CurrentAction = Action;
	SameAttackCount = (Action == LastAttack) ? SameAttackCount + 1 : 1;
	LastAttack = Action;

	ScheduleHitWindow(Action, Length);
	GetWorldTimerManager().SetTimer(ActionEndTimer, this, &AFishmanBoss::EndAction, FMath::Max(Length - 0.2f, 0.1f), false);
}

void AFishmanBoss::ScheduleHitWindow(EFishmanAction Action, float AnimLength)
{
	FTimerManager& Timers = GetWorldTimerManager();
	Timers.ClearTimer(HitStartTimer);
	Timers.ClearTimer(HitEndTimer);
	MeleeHit->EndHitWindow();

	// offsets are in mesh / bone space and scale with the mesh (mannequin mesh space: +Y = forward, Z = up from the feet);
	// radii are world cm
	auto Sphere = [this](FName Socket, const FVector& Offset, float Radius)
	{
		FMeleeHitShape S;
		S.Component = GetMesh();
		S.Socket = Socket;
		S.Start = Offset;
		S.End = Offset;
		S.Radius = Radius;
		return S;
	};

	TArray<FMeleeHitShape> Shapes;
	FVector2D Window;
	float Damage = 0.f;
	switch (Action)
	{
	case EFishmanAction::Slam:
		// both fists on the way down, plus the impact in front
		Shapes.Add(Sphere(TEXT("hand_l"), FVector::ZeroVector, 25.f * BossScale));
		Shapes.Add(Sphere(TEXT("hand_r"), FVector::ZeroVector, 25.f * BossScale));
		Shapes.Add(Sphere(NAME_None, FVector(0.f, 60.f, 10.f), 75.f * BossScale));
		Window = SlamHitWindow;
		Damage = SlamDamage;
		break;
	case EFishmanAction::JumpSlam:
		// shockwave all around the landing spot
		Shapes.Add(Sphere(NAME_None, FVector(0.f, 0.f, 20.f), JumpSlamRadius));
		Window = JumpSlamHitWindow;
		Damage = JumpSlamDamage;
		break;
	case EFishmanAction::StompRight:
	case EFishmanAction::StompLeft:
	{
		const FName Foot = (Action == EFishmanAction::StompRight) ? TEXT("ball_r") : TEXT("ball_l");
		Shapes.Add(Sphere(Foot, FVector::ZeroVector, 65.f * BossScale));
		Window = StompHitWindow;
		Damage = StompDamage;
		break;
	}
	default:
		return;
	}

	// AnimLength is real time (play rate included)
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

void AFishmanBoss::EndAction()
{
	FTimerManager& Timers = GetWorldTimerManager();
	Timers.ClearTimer(HitStartTimer);
	Timers.ClearTimer(HitEndTimer);
	MeleeHit->EndHitWindow();

	const EFishmanAction Finished = CurrentAction;
	CurrentAction = EFishmanAction::None;

	// phase 2 combos: one stomp into the other, slam into a jump
	if (bPhaseTwo && QueuedAction == EFishmanAction::None && FMath::FRand() < 0.5f)
	{
		if (Finished == EFishmanAction::StompRight)
		{
			QueuedAction = EFishmanAction::StompLeft;
		}
		else if (Finished == EFishmanAction::StompLeft)
		{
			QueuedAction = EFishmanAction::StompRight;
		}
		else if (Finished == EFishmanAction::Slam)
		{
			QueuedAction = EFishmanAction::JumpSlam;
		}
	}

	if (QueuedAction != EFishmanAction::None)
	{
		Decide();
	}
	else
	{
		EnterRecover();
	}
}

void AFishmanBoss::EnterRecover()
{
	State = EFishmanState::Recover;
	CurrentAction = EFishmanAction::None;
	SetLocomotionRate(true);
	const float Scale = bPhaseTwo ? PhaseTwoRecoverScale : 1.f;
	StateEndTime = GetWorld()->GetTimeSeconds() + FMath::FRandRange(RecoverTime.X, FMath::Max(RecoverTime.X, RecoverTime.Y)) * Scale;
}

// ---------------------------------------------------------------- damage / death / reset

float AFishmanBoss::TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator, AActor* DamageCauser)
{
	const float Damage = Super::TakeDamage(DamageAmount, DamageEvent, EventInstigator, DamageCauser);
	if (Damage <= 0.f || State == EFishmanState::Dead)
	{
		return 0.f;
	}

	// a boss doesn't flinch; hitting it wakes it up
	if (State == EFishmanState::Dormant)
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

void AFishmanBoss::HandleDeath(AActor* DamageCauser)
{
	State = EFishmanState::Dead;
	CurrentAction = EFishmanAction::None;
	QueuedAction = EFishmanAction::None;
	SetLocomotionRate(false);

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

	// collapse (mannequin physics asset)
	GetCharacterMovement()->DisableMovement();
	GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
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

void AFishmanBoss::ResetBoss()
{
	if (State == EFishmanState::Dead)
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

	TeleportTo(HomeTransform.GetLocation(), HomeTransform.Rotator(), false, true);
	GetCharacterMovement()->StopMovementImmediately();

	Stats->RestoreAll();
	bPhaseTwo = false;
	QueuedAction = EFishmanAction::None;
	CurrentAction = EFishmanAction::None;
	LastAttack = EFishmanAction::None;
	SameAttackCount = 0;
	State = EFishmanState::Dormant;
	SetLocomotionRate(true);
	ShowHealthBar(false);
}

// ---------------------------------------------------------------- boss health bar (bottom of the screen)

void AFishmanBoss::ShowHealthBar(bool bShow)
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
