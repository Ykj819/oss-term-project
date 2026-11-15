// Small wolf enemy (the boss's SK_Wolf scaled down): fast hit-and-run. It runs in to about 5m, crouches (readable wind-up),
// then leaps at the player and bites in mid-air. After landing it pauses (punish window), runs off to get distance and comes again.

#include "EnemyWolf.h"
#include "StatsComponent.h"
#include "MeleeHitComponent.h"
#include "Oss_TermProject.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr float WolfHalfHeight = 65.f;
	constexpr float WolfRadius = 40.f;
	const FName WolfSlot = TEXT("DefaultSlot");
}

AEnemyWolf::AEnemyWolf()
{
	GetCapsuleComponent()->InitCapsuleSize(WolfRadius, WolfHalfHeight);

	// the boss's wolf instead of the mannequin (faces -Y like the mannequin -> -90 yaw, origin at the feet)
	static ConstructorHelpers::FObjectFinder<USkeletalMesh> WolfMesh(TEXT("/Game/Characters/Wolf/SK_Wolf.SK_Wolf"));
	GetMesh()->SetSkeletalMeshAsset(WolfMesh.Succeeded() ? WolfMesh.Object : nullptr);
	GetMesh()->SetAnimInstanceClass(nullptr);	// ABP_Wolf is set in BeginPlay
	GetMesh()->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -WolfHalfHeight), FRotator(0.f, -90.f, 0.f));
	GetMesh()->SetRelativeScale3D(FVector(MeshScale));

	// mannequin animations don't fit this skeleton
	AttackAnimations.Reset();
	HeavyAttackAnimation.Reset();
	HitReactAnimation.Reset();
	RunAnim = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Wolf/Anims/Wolf_Run.Wolf_Run")));
	JumpBiteAnim = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Wolf/Anims/Wolf_Jump_Bite.Wolf_Jump_Bite")));

	ChaseSpeed = RunSpeed;
	GetCharacterMovement()->MaxWalkSpeed = RunSpeed;
	GetCharacterMovement()->RotationRate = FRotator(0.f, 720.f, 0.f);

	SightRange = 1500.f;
	LoseSightRange = 2500.f;
	SoulReward = 20;
	HealthBarHeight = 130.f;
	HealthBarSize = FVector2D(80.f, 6.f);
	HitStaggerTime = 0.4f;
	BaseEyeHeight = 60.f;
}

void AEnemyWolf::BeginPlay()
{
	ChaseSpeed = RunSpeed;
	GetMesh()->SetRelativeScale3D(FVector(MeshScale));

	Super::BeginPlay();

	if (UClass* Class = WolfAnimClass.LoadSynchronous())
	{
		GetMesh()->SetAnimInstanceClass(Class);
	}
	else
	{
		UE_LOG(LogOss_TermProject, Warning, TEXT("'%s': anim blueprint %s not found"), *GetNameSafe(this), *WolfAnimClass.ToString());
	}
	// the leap is driven by code: the bite's lunge (root motion) must not pull it around
	if (UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance())
	{
		AnimInstance->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	}
	RunAnim.LoadSynchronous();
	JumpBiteAnim.LoadSynchronous();

	if (UStatsComponent* EnemyStats = FindComponentByClass<UStatsComponent>())
	{
		EnemyStats->SetMaxHealth(MaxHealth);
		EnemyStats->RestoreAll();
	}

	SetPhase(EWolfPackPhase::Approach);
}

void AEnemyWolf::SetPhase(EWolfPackPhase NewPhase)
{
	Phase = NewPhase;
	PhaseStartTime = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.f;
}

void AEnemyWolf::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	if (State == EEnemyState::Dead)
	{
		return;
	}

	const float Now = GetWorld()->GetTimeSeconds();
	const float Elapsed = Now - PhaseStartTime;
	UCharacterMovementComponent* Movement = GetCharacterMovement();

	// the attack runs on its own clock (even if the player dies mid-leap)
	switch (Phase)
	{
	case EWolfPackPhase::WindUp:
		if (State == EEnemyState::Attack && Elapsed >= WindUpTime)
		{
			Launch();
		}
		break;

	case EWolfPackPhase::Leap:
		if ((Elapsed > 0.1f && Movement->IsMovingOnGround()) || Elapsed > LeapTime + 1.5f)
		{
			// landed: skids to a stop and stands there for a moment
			bFlinchOnHit = true;
			SetPhase(EWolfPackPhase::Land);
		}
		break;

	case EWolfPackPhase::Land:
		if (Elapsed >= LandRecoverTime)
		{
			FindComponentByClass<UMeleeHitComponent>()->EndHitWindow();
			Movement->bOrientRotationToMovement = true;
			NextJumpTime = Now + FMath::FRandRange(JumpCooldown.X, FMath::Max(JumpCooldown.X, JumpCooldown.Y));
			State = EEnemyState::Chase;
			SetPhase(EWolfPackPhase::Retreat);
		}
		break;

	default:
		break;
	}

	UpdateRunLoop();
}

void AEnemyWolf::TickCombat(APawn* Player, float Distance, float Now, float DeltaSeconds)
{
	UCharacterMovementComponent* Movement = GetCharacterMovement();

	if (Phase == EWolfPackPhase::WindUp)
	{
		// aims until it jumps
		FaceTowards(Player->GetActorLocation(), DeltaSeconds, 12.f);
		return;
	}
	if (Phase == EWolfPackPhase::Leap || Phase == EWolfPackPhase::Land)
	{
		return;
	}

	if (Distance > LoseSightRange)
	{
		State = EEnemyState::Idle;
		return;
	}

	FVector ToPlayer = Player->GetActorLocation() - GetActorLocation();
	ToPlayer.Z = 0.f;
	ToPlayer = ToPlayer.GetSafeNormal();
	Movement->bOrientRotationToMovement = true;

	if (Phase == EWolfPackPhase::Retreat)
	{
		// runs off to get leaping distance
		Movement->MaxWalkSpeed = RunSpeed;
		AddMovementInput(-ToPlayer);
		if (Distance >= RetreatDistance || Now - PhaseStartTime > 2.5f)
		{
			SetPhase(EWolfPackPhase::Approach);
		}
		return;
	}

	// Approach
	if (Distance < MinJumpRange)
	{
		SetPhase(EWolfPackPhase::Retreat);
		return;
	}

	if (Distance <= JumpBiteRange && Now >= NextJumpTime && CanSee(Player))
	{
		StartWindUp(Player);
		return;
	}

	if (Distance > JumpBiteRange - 40.f)
	{
		// run in
		Movement->MaxWalkSpeed = RunSpeed;
		AddMovementInput(ToPlayer);
	}
	else
	{
		// in range but not ready yet: circle the player, keeping the distance
		if (Now >= CircleSwitchTime)
		{
			CircleDirection = FMath::RandBool() ? 1.f : -1.f;
			CircleSwitchTime = Now + FMath::FRandRange(1.5f, 3.f);
		}
		Movement->MaxWalkSpeed = RunSpeed * 0.6f;
		const FVector Tangent = FVector::CrossProduct(FVector::UpVector, ToPlayer) * CircleDirection;
		const float KeepOut = Distance < (MinJumpRange + JumpBiteRange) * 0.5f ? -0.4f : 0.2f;
		AddMovementInput((Tangent + ToPlayer * KeepOut).GetSafeNormal());
	}
}

void AEnemyWolf::StartWindUp(APawn* Player)
{
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->StopMovementImmediately();
	Movement->bOrientRotationToMovement = false;
	State = EEnemyState::Attack;
	SetPhase(EWolfPackPhase::WindUp);

	// the bite is timed so the jaws snap just before it lands
	LoopMontage = nullptr;
	if (UAnimSequenceBase* Anim = JumpBiteAnim.Get())
	{
		if (UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance())
		{
			const float SnapTime = WindUpTime + LeapTime * 0.85f;
			const float Rate = FMath::Clamp(Anim->GetPlayLength() * BiteSnapFraction / FMath::Max(SnapTime, 0.1f), 0.2f, 4.f);
			AnimInstance->PlaySlotAnimationAsDynamicMontage(Anim, WolfSlot, 0.15f, 0.3f, Rate);
		}
	}
}

void AEnemyWolf::Launch()
{
	APawn* Player = GetPlayer();
	if (!Player)
	{
		CancelAttack();
		State = EEnemyState::Chase;
		return;
	}

	// ballistic jump that lands just short of where the player is now (moving / rolling away dodges it)
	const FVector Start = GetActorLocation();
	FVector ToPlayer = Player->GetActorLocation() - Start;
	ToPlayer.Z = 0.f;
	const FVector Dir = ToPlayer.GetSafeNormal();
	const float Horizontal = FMath::Max(ToPlayer.Size() - LandShortOfPlayer, 50.f);
	FVector Target = Start + Dir * Horizontal;
	Target.Z = Player->GetActorLocation().Z - Player->GetSimpleCollisionHalfHeight() + WolfHalfHeight;

	const float T = FMath::Max(LeapTime, 0.1f);
	const float Gravity = -GetCharacterMovement()->GetGravityZ();
	FVector Velocity = (Target - Start) / T;
	Velocity.Z = (Target.Z - Start.Z) / T + 0.5f * Gravity * T;

	if (!Dir.IsNearlyZero())
	{
		SetActorRotation(Dir.Rotation());
	}
	LaunchCharacter(Velocity, true, true);

	// can't be knocked out of the air
	bFlinchOnHit = false;
	SetPhase(EWolfPackPhase::Leap);

	// jaws dangerous from mid-flight until just after landing
	FTimerManager& Timers = GetWorldTimerManager();
	Timers.SetTimer(HitWindowStartTimer, this, &AEnemyWolf::OpenBiteWindow, FMath::Max(T * 0.35f, 0.01f), false);
	Timers.SetTimer(HitWindowEndTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		FindComponentByClass<UMeleeHitComponent>()->EndHitWindow();
	}), T + 0.15f, false);
}

void AEnemyWolf::OpenBiteWindow()
{
	// bone segments run along the bone (+Y as exported from Blender); lengths scale with the mesh
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
	Shapes.Add(Shape(TEXT("head"), 100.f, 28.f));
	Shapes.Add(Shape(TEXT("jaw"), 75.f, 22.f));

	UMeleeHitComponent* Hit = FindComponentByClass<UMeleeHitComponent>();
	Hit->bDebugDraw = bDebugBite;
	Hit->BeginHitWindow(Shapes, JumpBiteDamage);
}

void AEnemyWolf::CancelAttack()
{
	Super::CancelAttack();

	// interrupted (hit during the crouch, death, reset): start over
	bFlinchOnHit = true;
	if (Phase == EWolfPackPhase::WindUp || Phase == EWolfPackPhase::Leap || Phase == EWolfPackPhase::Land)
	{
		NextJumpTime = GetWorld()->GetTimeSeconds() + 1.f;
		SetPhase(EWolfPackPhase::Approach);
	}
}

void AEnemyWolf::UpdateRunLoop()
{
	UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance();
	UAnimSequenceBase* Anim = RunAnim.Get();
	if (!AnimInstance || !Anim)
	{
		return;
	}

	// only while running around (the attack plays its own animation; a flinch stops the slot)
	const bool bMovingPhase = (Phase == EWolfPackPhase::Approach || Phase == EWolfPackPhase::Retreat)
		&& (State == EEnemyState::Chase || State == EEnemyState::Idle);
	const float Speed = GetVelocity().Size2D();

	if (bMovingPhase && Speed > 20.f)
	{
		// small legs move faster: rate = speed / what the animation covers at this size
		const float Rate = FMath::Clamp(Speed / FMath::Max(RunAnimSpeedAtFullScale * MeshScale, 1.f), 0.3f, MaxRunAnimRate);
		if (LoopMontage && AnimInstance->Montage_IsPlaying(LoopMontage))
		{
			AnimInstance->Montage_SetPlayRate(LoopMontage, Rate);
		}
		else
		{
			LoopMontage = AnimInstance->PlaySlotAnimationAsDynamicMontage(Anim, WolfSlot, 0.2f, 0.2f, Rate, 100000);
		}
	}
	else if (bMovingPhase && LoopMontage)
	{
		if (AnimInstance->Montage_IsPlaying(LoopMontage))
		{
			AnimInstance->Montage_Stop(0.25f, LoopMontage);
		}
		LoopMontage = nullptr;
	}
}

void AEnemyWolf::ResetEnemy()
{
	Super::ResetEnemy();

	ChaseSpeed = RunSpeed;
	GetCharacterMovement()->MaxWalkSpeed = RunSpeed;
	bFlinchOnHit = true;
	LoopMontage = nullptr;
	NextJumpTime = 0.f;
	SetPhase(EWolfPackPhase::Approach);
}
