// Spiked ball enemy: only charges. Revs up in place (warning), rolls straight at where the player was,
// then sits dazed for a few seconds before it can move again (the window to punish it)

#include "EnemyBall.h"
#include "StatsComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/DamageType.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"
#include "Oss_TermProjectCharacter.h"

AEnemyBall::AEnemyBall()
{
	GetCapsuleComponent()->InitCapsuleSize(BallRadius, BallRadius);

	// no body: the mannequin from the base class is removed
	GetMesh()->SetSkeletalMeshAsset(nullptr);
	GetMesh()->SetAnimInstanceClass(nullptr);
	GetMesh()->SetVisibility(false);
	GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	AttackAnimations.Reset();
	HeavyAttackAnimation.Reset();
	HitReactAnimation.Reset();

	SightRange = 1800.f;
	LoseSightRange = 2600.f;
	FirstAttackDelay = 0.3f;
	SoulReward = 15;
	HealthBarHeight = 100.f;
	bFlinchOnHit = false;	// hits never cancel the charge or shorten the rest
	BaseEyeHeight = 20.f;

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->bOrientRotationToMovement = false;
	Movement->bCanWalkOffLedges = false;	// a charge stops at a ledge instead of rolling off the arena

	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphereMesh(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> ConeMesh(TEXT("/Engine/BasicShapes/Cone.Cone"));

	BallPivot = CreateDefaultSubobject<USceneComponent>(TEXT("BallPivot"));
	BallPivot->SetupAttachment(RootComponent);
	BallPivot->SetUsingAbsoluteRotation(true);

	auto Configure = [](UStaticMeshComponent* Part)
	{
		Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Part->SetGenerateOverlapEvents(false);
		Part->SetCanEverAffectNavigation(false);
	};

	// engine sphere: 100 wide, centered
	Ball = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Ball"));
	Ball->SetupAttachment(BallPivot);
	Ball->SetRelativeScale3D(FVector(BallRadius / 50.f));
	Configure(Ball);
	if (SphereMesh.Succeeded())
	{
		Ball->SetStaticMesh(SphereMesh.Object);
	}

	// spikes on the 6 axes + 8 diagonals, so the rolling is easy to see (engine cone: 100 wide/tall, centered, points +Z)
	TArray<FVector> Dirs = { FVector::XAxisVector, -FVector::XAxisVector, FVector::YAxisVector, -FVector::YAxisVector, FVector::ZAxisVector, -FVector::ZAxisVector };
	for (int32 X = -1; X <= 1; X += 2)
	{
		for (int32 Y = -1; Y <= 1; Y += 2)
		{
			for (int32 Z = -1; Z <= 1; Z += 2)
			{
				Dirs.Add(FVector(X, Y, Z).GetSafeNormal());
			}
		}
	}
	for (int32 i = 0; i < Dirs.Num(); ++i)
	{
		UStaticMeshComponent* Spike = CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("Spike%d"), i));
		Spike->SetupAttachment(BallPivot);
		Configure(Spike);
		if (ConeMesh.Succeeded())
		{
			Spike->SetStaticMesh(ConeMesh.Object);
		}
		const float Length = BallRadius * 0.55f;
		Spike->SetRelativeRotation(FRotationMatrix::MakeFromZ(Dirs[i]).Rotator());
		Spike->SetRelativeLocation(Dirs[i] * (BallRadius * 0.85f + Length * 0.5f));
		Spike->SetRelativeScale3D(FVector(BallRadius * 0.4f / 100.f, BallRadius * 0.4f / 100.f, Length / 100.f));
		Spikes.Add(Spike);
	}
}

void AEnemyBall::BeginPlay()
{
	Super::BeginPlay();

	if (UStatsComponent* EnemyStats = FindComponentByClass<UStatsComponent>())
	{
		EnemyStats->SetMaxHealth(MaxHealth);
		EnemyStats->RestoreAll();
	}

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	DefaultMaxAcceleration = Movement->MaxAcceleration;
	DefaultBraking = Movement->BrakingDecelerationWalking;
	Movement->bOrientRotationToMovement = false;

	BallMaterials.Reset();
	if (UMaterialInstanceDynamic* MID = Ball->CreateDynamicMaterialInstance(0))
	{
		BallMaterials.Add(MID);
	}
	for (UStaticMeshComponent* Spike : Spikes)
	{
		if (UMaterialInstanceDynamic* MID = Spike->CreateDynamicMaterialInstance(0))
		{
			BallMaterials.Add(MID);
		}
	}
	SetGlow(0.f);
}

void AEnemyBall::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	const float Now = GetWorld()->GetTimeSeconds();

	// dead: the ball deflates and sinks, then the base class hides it
	if (State == EEnemyState::Dead)
	{
		if (DeathTime < 0.f)
		{
			DeathTime = Now;
			SetGlow(0.f);
		}
		const float T = FMath::Clamp((Now - DeathTime) / 0.6f, 0.f, 1.f);
		BallPivot->SetRelativeScale3D(FVector(FMath::Lerp(1.f, 0.05f, T * T)));
		BallPivot->SetRelativeLocation(FVector(0.f, 0.f, -BallRadius * T));
		return;
	}

	// rolls whenever it moves (approach, charge, bounce)
	RollBall(GetVelocity(), DeltaSeconds);

	switch (Phase)
	{
	case EBallPhase::WindUp:
	{
		// revs up: spins in place faster and faster, glowing brighter
		const float T = FMath::Clamp((Now - PhaseStartTime) / FMath::Max(WindUpTime, 0.01f), 0.f, 1.f);
		const FVector Axis = FVector::CrossProduct(FVector::UpVector, ChargeDir).GetSafeNormal();
		BallPivot->AddWorldRotation(FQuat(Axis, FMath::DegreesToRadians(200.f + 1100.f * T) * DeltaSeconds));
		SetGlow(T * (0.75f + 0.25f * FMath::Sin(Now * 30.f)));
		break;
	}
	case EBallPhase::Resting:
	{
		// dazed: wobbles, the glow fades out
		const float T = Now - PhaseStartTime;
		BallPivot->SetRelativeLocation(FVector(FMath::Sin(T * 9.f) * 3.f, FMath::Cos(T * 7.f) * 3.f, 0.f));
		SetGlow(FMath::Max(0.f, 0.6f - T));
		break;
	}
	default:
		break;
	}
}

void AEnemyBall::TickCombat(APawn* Player, float Distance, float Now, float DeltaSeconds)
{
	switch (Phase)
	{
	case EBallPhase::Ready:
	{
		if (Distance > LoseSightRange)
		{
			State = EEnemyState::Idle;
			return;
		}
		if (Now < NextAttackTime)
		{
			return;
		}
		if (Distance <= ChargeRange && CanSee(Player))
		{
			FVector Dir = Player->GetActorLocation() - GetActorLocation();
			Dir.Z = 0.f;
			ChargeDir = Dir.GetSafeNormal();
			StartWindUp(Now);
		}
		else
		{
			// too far / no clear line: roll slowly closer
			FVector Dir = Player->GetActorLocation() - GetActorLocation();
			Dir.Z = 0.f;
			AddMovementInput(Dir.GetSafeNormal());
		}
		break;
	}

	case EBallPhase::WindUp:
	{
		// aims while revving up; the direction is locked when it launches
		FVector Dir = Player->GetActorLocation() - GetActorLocation();
		Dir.Z = 0.f;
		if (!Dir.IsNearlyZero())
		{
			ChargeDir = Dir.GetSafeNormal();
		}
		if (Now - PhaseStartTime >= WindUpTime)
		{
			StartCharge(Player, Now);
		}
		break;
	}

	case EBallPhase::Charging:
	{
		AddMovementInput(ChargeDir);
		TryHitPlayer(Player);
		if (Phase != EBallPhase::Charging)
		{
			break;	// the hit ended the charge
		}

		const float Travelled = FVector::Dist2D(GetActorLocation(), ChargeStart);
		const bool bBlocked = Now - PhaseStartTime > 0.3f && GetVelocity().Size2D() < ChargeSpeed * 0.3f;
		if (bBlocked)
		{
			EndCharge(Now, true);	// wall / ledge
		}
		else if (Travelled >= ChargeDistance)
		{
			EndCharge(Now, false);
		}
		break;
	}

	case EBallPhase::Resting:
		if (Now - PhaseStartTime >= RestTime)
		{
			Phase = EBallPhase::Ready;
			BallPivot->SetRelativeLocation(FVector::ZeroVector);
			GetCharacterMovement()->BrakingDecelerationWalking = DefaultBraking;
			SetGlow(0.f);
		}
		break;
	}
}

void AEnemyBall::StartWindUp(float Now)
{
	Phase = EBallPhase::WindUp;
	State = EEnemyState::Attack;
	PhaseStartTime = Now;
	GetCharacterMovement()->StopMovementImmediately();
}

void AEnemyBall::StartCharge(APawn* Player, float Now)
{
	Phase = EBallPhase::Charging;
	PhaseStartTime = Now;
	ChargeStart = GetActorLocation();
	ChargeDistance = FMath::Min(FVector::Dist2D(ChargeStart, Player->GetActorLocation()) + ChargeOvershoot, MaxChargeDistance);
	bChargeResolved = false;

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->MaxWalkSpeed = ChargeSpeed;
	Movement->MaxAcceleration = ChargeSpeed * 8.f;
	Movement->Velocity = ChargeDir * ChargeSpeed * 0.6f;	// launches off the spot

	// rolls through pawns: a dodge-rolling player lets it pass, and it doesn't get stuck on other enemies
	SetPassThroughPawns(true);
	SetGlow(1.f);
}

void AEnemyBall::TryHitPlayer(APawn* Player)
{
	if (bChargeResolved)
	{
		return;
	}

	const UCapsuleComponent* PlayerCapsule = Cast<UCapsuleComponent>(Player->GetRootComponent());
	const float PlayerRadius = PlayerCapsule ? PlayerCapsule->GetScaledCapsuleRadius() : 40.f;
	const float PlayerHalfHeight = PlayerCapsule ? PlayerCapsule->GetScaledCapsuleHalfHeight() : 90.f;
	const FVector P = Player->GetActorLocation();
	const FVector B = GetActorLocation();
	if (FVector::Dist2D(P, B) > PlayerRadius + BallRadius + 10.f || FMath::Abs(P.Z - B.Z) > PlayerHalfHeight + BallRadius)
	{
		return;
	}

	bChargeResolved = true;

	// rolled through it: keeps going behind the player
	if (const AOss_TermProjectCharacter* PlayerCharacter = Cast<AOss_TermProjectCharacter>(Player))
	{
		if (PlayerCharacter->IsDodging())
		{
			UGameplayStatics::ApplyDamage(Player, ChargeDamage, GetController(), this, UDamageType::StaticClass());	// shows "DODGE"
			return;
		}
	}

	const float Taken = UGameplayStatics::ApplyDamage(Player, ChargeDamage, GetController(), this, UDamageType::StaticClass());

	// a real hit knocks the player away (a block doesn't)
	if (Taken > 0.f)
	{
		if (ACharacter* PlayerChar = Cast<ACharacter>(Player))
		{
			PlayerChar->LaunchCharacter(ChargeDir * KnockbackSpeed + FVector(0.f, 0.f, 250.f), true, true);
		}
	}

	// smacked into the player (or their guard): bounces off and stops
	EndCharge(GetWorld()->GetTimeSeconds(), true);
}

void AEnemyBall::EndCharge(float Now, bool bBounce)
{
	SetPassThroughPawns(false);

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->MaxWalkSpeed = ChaseSpeed;
	Movement->MaxAcceleration = DefaultMaxAcceleration;

	if (bBounce)
	{
		Movement->StopMovementImmediately();
		LaunchCharacter(-ChargeDir * 350.f + FVector(0.f, 0.f, 300.f), true, true);
	}
	else
	{
		// rolls out a little instead of stopping dead
		Movement->BrakingDecelerationWalking = ChargeSpeed * 1.5f;
		Movement->Velocity = ChargeDir * FMath::Min(Movement->Velocity.Size2D(), ChargeSpeed * 0.5f);
	}

	Phase = EBallPhase::Resting;
	State = EEnemyState::Chase;
	PhaseStartTime = Now;
	NextAttackTime = Now + RestTime;
}

void AEnemyBall::CancelAttack()
{
	Super::CancelAttack();

	if (UCharacterMovementComponent* Movement = GetCharacterMovement())
	{
		Movement->bOrientRotationToMovement = false;
		Movement->MaxWalkSpeed = ChaseSpeed;
		Movement->MaxAcceleration = DefaultMaxAcceleration;
		Movement->BrakingDecelerationWalking = DefaultBraking;
	}
	SetPassThroughPawns(false);
	Phase = EBallPhase::Ready;
	SetGlow(0.f);
}

void AEnemyBall::ResetEnemy()
{
	Super::ResetEnemy();

	GetCharacterMovement()->bOrientRotationToMovement = false;
	GetCharacterMovement()->BrakingDecelerationWalking = DefaultBraking;
	Phase = EBallPhase::Ready;
	DeathTime = -1.f;
	BallPivot->SetRelativeScale3D(FVector::OneVector);
	BallPivot->SetRelativeLocation(FVector::ZeroVector);
	SetGlow(0.f);
}

void AEnemyBall::RollBall(const FVector& Velocity, float DeltaSeconds)
{
	const FVector Flat(Velocity.X, Velocity.Y, 0.f);
	const float Speed = Flat.Size();
	if (Speed < 1.f || Phase == EBallPhase::WindUp)
	{
		return;
	}
	const FVector Axis = FVector::CrossProduct(FVector::UpVector, Flat / Speed);
	BallPivot->AddWorldRotation(FQuat(Axis, Speed * DeltaSeconds / BallRadius));
}

void AEnemyBall::SetGlow(float Alpha)
{
	const FLinearColor Color = FMath::Lerp(BallColor, WarningColor, FMath::Clamp(Alpha, 0.f, 1.f));
	for (UMaterialInstanceDynamic* MID : BallMaterials)
	{
		if (MID)
		{
			MID->SetVectorParameterValue(TEXT("Color"), Color);
		}
	}
}

void AEnemyBall::SetPassThroughPawns(bool bPass)
{
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn, bPass ? ECR_Ignore : ECR_Block);
}
