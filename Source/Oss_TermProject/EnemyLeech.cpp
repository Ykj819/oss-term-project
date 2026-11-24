// Small leech enemy: lies still on the ground. When the player comes close it rears up (readable wind-up) and leaps onto
// the player's body, then drains health every second (blocking doesn't help, a roll at the right moment dodges the leap).
// It can't be hit: pressing E (interact) ShakeOffPresses times pulls it off, and it dies when it hits the ground.

#include "EnemyLeech.h"
#include "StatsComponent.h"
#include "Oss_TermProjectCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr float LeechHalfHeight = 14.f;
	constexpr float LeechRadius = 16.f;
	constexpr int32 NumSegments = 7;
	const FVector DefaultSpot(-15.f, 0.f, 45.f);
}

AEnemyLeech::AEnemyLeech()
{
	GetCapsuleComponent()->InitCapsuleSize(LeechRadius, LeechHalfHeight);

	// no mannequin: the body is built from spheres
	GetMesh()->SetSkeletalMeshAsset(nullptr);
	GetMesh()->SetAnimInstanceClass(nullptr);
	GetMesh()->SetVisibility(false);
	GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	AttackAnimations.Reset();
	HeavyAttackAnimation.Reset();
	HitReactAnimation.Reset();

	// doesn't crawl around: it only turns and leaps
	ChaseSpeed = 0.f;
	GetCharacterMovement()->MaxWalkSpeed = 0.f;
	GetCharacterMovement()->bOrientRotationToMovement = false;

	SightRange = 700.f;
	LoseSightRange = 1000.f;
	SoulReward = 5;

	// no hit detection: attacks pass through it (the only way to kill it is pulling it off), and it isn't a lock-on target
	SetCanBeDamaged(false);
	Tags.Remove(TEXT("LockOnTarget"));
	HealthBarHeight = 45.f;
	HealthBarSize = FVector2D(45.f, 5.f);
	bFlinchOnHit = false;
	BaseEyeHeight = 10.f;
	CorpseLifeSpan = 4.f;

	// back high, back low, chest, belly (player capsule half height is 96)
	AttachSpots = {
		FVector(-15.f,  0.f, 45.f),
		FVector(-13.f,  5.f, 12.f),
		FVector( 14.f, -3.f, 38.f),
		FVector( 13.f,  4.f,  5.f),
	};

	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphereMesh(TEXT("/Engine/BasicShapes/Sphere.Sphere"));

	BodyRoot = CreateDefaultSubobject<USceneComponent>(TEXT("BodyRoot"));
	BodyRoot->SetupAttachment(RootComponent);
	BodyRoot->SetRelativeLocation(FVector(0.f, 0.f, -LeechHalfHeight));

	// project material (param Color): the engine shapes' default BasicShapeMaterial showed the grey grid
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> SolidMat(TEXT("/Game/Characters/Enemies/Materials/M_EnemySolid.M_EnemySolid"));
	auto MakePart = [&](const TCHAR* Name)
	{
		UStaticMeshComponent* Part = CreateDefaultSubobject<UStaticMeshComponent>(Name);
		if (SolidMat.Succeeded())
		{
			Part->SetMaterial(0, SolidMat.Object);
		}
		Part->SetupAttachment(BodyRoot);
		Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Part->SetGenerateOverlapEvents(false);
		Part->SetCanEverAffectNavigation(false);
		if (SphereMesh.Succeeded())
		{
			Part->SetStaticMesh(SphereMesh.Object);
		}
		return Part;
	};

	// segments from the head (front, +X) to the tail: thin head, fat middle, round sucker tail (engine sphere is 100 wide)
	const float Radii[NumSegments] = { 4.5f, 6.f, 7.5f, 8.5f, 8.5f, 7.5f, 6.5f };
	for (int32 i = 0; i < NumSegments; ++i)
	{
		UStaticMeshComponent* Seg = MakePart(*FString::Printf(TEXT("Segment%d"), i));
		const float R = Radii[i];
		Seg->SetRelativeLocation(FVector(16.f - i * 5.4f, 0.f, R * 0.6f));
		Seg->SetRelativeScale3D(FVector(R * 2.6f, R * 2.f, R * 1.2f) / 100.f);
		Segments.Add(Seg);
	}
	Mouth = MakePart(TEXT("Mouth"));
	Mouth->SetRelativeLocation(FVector(19.5f, 0.f, 2.8f));
	Mouth->SetRelativeScale3D(FVector(0.05f, 0.065f, 0.045f));
}

void AEnemyLeech::BeginPlay()
{
	Super::BeginPlay();

	if (UStatsComponent* EnemyStats = FindComponentByClass<UStatsComponent>())
	{
		EnemyStats->SetMaxHealth(MaxHealth);
		EnemyStats->RestoreAll();
	}
	GetCharacterMovement()->MaxWalkSpeed = 0.f;
	GetCharacterMovement()->bOrientRotationToMovement = false;

	SegmentBaseLocations.Reset();
	SegmentBaseScales.Reset();
	SegmentMaterials.Reset();
	for (int32 i = 0; i < Segments.Num(); ++i)
	{
		SegmentBaseLocations.Add(Segments[i]->GetRelativeLocation());
		SegmentBaseScales.Add(Segments[i]->GetRelativeScale3D());
		UMaterialInstanceDynamic* MID = Segments[i]->CreateDynamicMaterialInstance(0);
		if (MID)
		{
			// faint banding between segments
			MID->SetVectorParameterValue(TEXT("Color"), BodyColor * (i % 2 == 0 ? 1.f : 1.35f));
		}
		SegmentMaterials.Add(MID);
	}
	if (UMaterialInstanceDynamic* MID = Mouth->CreateDynamicMaterialInstance(0))
	{
		MID->SetVectorParameterValue(TEXT("Color"), MouthColor);
	}

	SetPhase(ELeechPhase::Resting);
}

void AEnemyLeech::SetPhase(ELeechPhase NewPhase)
{
	Phase = NewPhase;
	PhaseStartTime = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.f;
}

void AEnemyLeech::SetGroundMode(bool bOnGround)
{
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	if (bOnGround)
	{
		GetCapsuleComponent()->SetCollisionEnabled(CapsuleCollision);
		Movement->SetMovementMode(MOVE_Falling);
	}
	else
	{
		// stuck to / flying at the player: moved by hand, touches nothing
		GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Movement->StopMovementImmediately();
		Movement->SetMovementMode(MOVE_None);
	}
}

void AEnemyLeech::TickCombat(APawn* Player, float Distance, float Now, float DeltaSeconds)
{
	if (Phase == ELeechPhase::Resting)
	{
		if (Distance > LoseSightRange)
		{
			State = EEnemyState::Idle;
			return;
		}

		// noticed: slowly turns its head toward the player, leaps when close enough
		FaceTowards(Player->GetActorLocation(), DeltaSeconds, 2.f);
		if (Distance <= LatchRange && Now >= NextLatchTime && GetCharacterMovement()->IsMovingOnGround() && CanSee(Player))
		{
			StartWindUp(Player);
		}
	}
	else if (Phase == ELeechPhase::WindUp)
	{
		FaceTowards(Player->GetActorLocation(), DeltaSeconds, 8.f);
	}
}

void AEnemyLeech::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	const float Now = GetWorld()->GetTimeSeconds();

	if (State == EEnemyState::Dead)
	{
		if (DeathTime < 0.f)
		{
			DeathTime = Now;
			DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
			AttachedPlayer.Reset();
			Phase = ELeechPhase::Resting;

			// killed in mid-air (thrown off): drop onto the ground, upright
			FHitResult Hit;
			FCollisionQueryParams Params(SCENE_QUERY_STAT(LeechGround), false, this);
			const FVector From = GetActorLocation();
			if (GetWorld()->LineTraceSingleByChannel(Hit, From, From - FVector(0.f, 0.f, 2000.f), ECC_Visibility, Params))
			{
				SetActorLocation(Hit.ImpactPoint + FVector(0.f, 0.f, LeechHalfHeight));
			}
			SetActorRotation(FRotator(0.f, GetActorRotation().Yaw, 0.f));
		}
		UpdateBody(DeltaSeconds, Now);
		return;
	}

	switch (Phase)
	{
	case ELeechPhase::WindUp:
		if (Now - PhaseStartTime >= WindUpTime)
		{
			StartLeap();
		}
		break;

	case ELeechPhase::Leaping:
		UpdateLeap(Now);
		break;

	case ELeechPhase::Attached:
		UpdateAttached(DeltaSeconds, Now);
		break;

	case ELeechPhase::Recovering:
		if (bShakenOff)
		{
			// pulled off: dies when it hits the ground (souls go to the player)
			if ((Now - PhaseStartTime > 0.1f && GetCharacterMovement()->IsMovingOnGround()) || Now - PhaseStartTime >= ShakenOffMaxFallTime)
			{
				if (UStatsComponent* EnemyStats = FindComponentByClass<UStatsComponent>())
				{
					EnemyStats->ApplyDamage(EnemyStats->GetHealth() + 1.f, AttachedPlayer.Get());
				}
			}
		}
		else if (Now - PhaseStartTime >= RecoverDuration && GetCharacterMovement()->IsMovingOnGround())
		{
			SetPhase(ELeechPhase::Resting);
			NextLatchTime = Now + RelatchCooldown;
		}
		break;

	default:
		break;
	}

	UpdateBody(DeltaSeconds, Now);
}

int32 AEnemyLeech::PickAttachSpot(const APawn* Player) const
{
	if (AttachSpots.Num() == 0 || !Player)
	{
		return 0;
	}

	// the body side facing the leech, with a little randomness
	FVector ToLeech = Player->GetActorTransform().InverseTransformVectorNoScale(GetActorLocation() - Player->GetActorLocation());
	ToLeech.Z = 0.f;
	ToLeech = ToLeech.GetSafeNormal();

	int32 Best = 0;
	float BestScore = -1000.f;
	for (int32 i = 0; i < AttachSpots.Num(); ++i)
	{
		const FVector Normal = FVector(AttachSpots[i].X, AttachSpots[i].Y, 0.f).GetSafeNormal();
		const float Score = FVector::DotProduct(Normal, ToLeech) + FMath::FRandRange(0.f, 0.35f);
		if (Score > BestScore)
		{
			BestScore = Score;
			Best = i;
		}
	}
	return Best;
}

FTransform AEnemyLeech::GetSpotTransform(int32 SpotIndex) const
{
	const FVector Spot = AttachSpots.IsValidIndex(SpotIndex) ? AttachSpots[SpotIndex] : DefaultSpot;
	FVector Normal = FVector(Spot.X, Spot.Y, 0.f).GetSafeNormal();
	if (Normal.IsNearlyZero())
	{
		Normal = -FVector::ForwardVector;
	}

	// belly (BodyRoot, LeechHalfHeight below the origin) flat on the body, head pointing up and a bit to the side
	const FVector HeadDir = FQuat(Normal, FMath::DegreesToRadians(AttachRoll)).RotateVector(FVector::UpVector);
	const FRotator Rotation = FRotationMatrix::MakeFromZX(Normal, HeadDir).Rotator();
	return FTransform(Rotation, Spot + Normal * LeechHalfHeight);
}

void AEnemyLeech::StartWindUp(APawn* Player)
{
	AttachedPlayer = Player;
	AttachSpotIndex = PickAttachSpot(Player);
	AttachRoll = FMath::FRandRange(-30.f, 30.f);
	State = EEnemyState::Chase;
	SetPhase(ELeechPhase::WindUp);
}

void AEnemyLeech::StartLeap()
{
	APawn* Player = AttachedPlayer.Get();
	if (!Player || GetPlayer() != Player)
	{
		AttachedPlayer.Reset();
		SetPhase(ELeechPhase::Resting);
		return;
	}

	LeapStart = GetActorLocation();
	LeapStartQuat = GetActorQuat();
	LeapDir = (Player->GetActorLocation() - LeapStart).GetSafeNormal2D();
	SetGroundMode(false);
	SetPhase(ELeechPhase::Leaping);
}

void AEnemyLeech::UpdateLeap(float Now)
{
	APawn* Player = AttachedPlayer.Get();
	if (!Player || GetPlayer() != Player)
	{
		Detach(false);
		return;
	}

	const float T = FMath::Clamp((Now - PhaseStartTime) / FMath::Max(LeapDuration, 0.05f), 0.f, 1.f);

	// a roll (invincible part) near the end of the flight dodges it: it sails past and drops
	if (T >= 0.55f)
	{
		if (const AOss_TermProjectCharacter* PlayerCharacter = Cast<AOss_TermProjectCharacter>(Player))
		{
			if (PlayerCharacter->IsDodging())
			{
				Detach(false);
				return;
			}
		}
	}

	// homes in on the body spot (it moves with the player), in an arc
	const FTransform Target = GetSpotTransform(AttachSpotIndex) * Player->GetRootComponent()->GetComponentTransform();
	const FVector Pos = FMath::Lerp(LeapStart, Target.GetLocation(), T) + FVector::UpVector * LeapArcHeight * 4.f * T * (1.f - T);
	const FQuat Rot = FQuat::Slerp(LeapStartQuat, Target.GetRotation(), FMath::Min(T * 1.4f, 1.f));
	SetActorLocationAndRotation(Pos, Rot);

	if (T >= 1.f)
	{
		Attach(Player);
	}
}

void AEnemyLeech::Attach(APawn* Player)
{
	AttachToComponent(Player->GetRootComponent(), FAttachmentTransformRules::KeepWorldTransform);
	GetRootComponent()->SetRelativeTransform(GetSpotTransform(AttachSpotIndex));

	ShakeCount = 0;
	DrainTimer = 0.f;
	DrunkAmount = 0.f;
	LastShakeTime = -1000.f;
	SetPhase(ELeechPhase::Attached);

	// can't be locked on to while on the player's body (also drops a current lock)
	Tags.Remove(TEXT("LockOnTarget"));
	ShowHint();
}

void AEnemyLeech::UpdateAttached(float DeltaSeconds, float Now)
{
	APawn* Player = AttachedPlayer.Get();
	if (!Player || GetPlayer() != Player)
	{
		// player died / is gone: falls off
		Detach(false);
		return;
	}

	// drain straight from health: no block, no flinch
	DrainTimer += DeltaSeconds;
	while (DrainTimer >= DrainInterval)
	{
		DrainTimer -= DrainInterval;
		if (UStatsComponent* PlayerStats = Player->FindComponentByClass<UStatsComponent>())
		{
			DrunkAmount += PlayerStats->ApplyDamage(DrainPerSecond * DrainInterval, this);
		}
	}

	ShowHint();
}

bool AEnemyLeech::TryShakeOff(APawn* Player)
{
	if (!Player || !Player->GetWorld())
	{
		return false;
	}

	// presses go to the leech that latched on first, then the next one
	AEnemyLeech* Oldest = nullptr;
	for (TActorIterator<AEnemyLeech> It(Player->GetWorld()); It; ++It)
	{
		if (It->IsAttachedToPlayer(Player) && (!Oldest || It->PhaseStartTime < Oldest->PhaseStartTime))
		{
			Oldest = *It;
		}
	}
	if (!Oldest)
	{
		return false;
	}

	Oldest->RegisterShakePress();
	return true;
}

void AEnemyLeech::RegisterShakePress()
{
	++ShakeCount;
	LastShakeTime = GetWorld()->GetTimeSeconds();
	if (ShakeCount >= ShakeOffPresses)
	{
		Detach(true);
	}
	else
	{
		ShowHint();
	}
}

void AEnemyLeech::Detach(bool bThrown)
{
	APawn* Player = AttachedPlayer.Get();
	const bool bWasAttached = Phase == ELeechPhase::Attached && Player;

	// direction away from the body it was stuck to
	FVector Out = -LeapDir;
	if (bWasAttached)
	{
		const FTransform Spot = GetSpotTransform(AttachSpotIndex) * Player->GetRootComponent()->GetComponentTransform();
		Out = Spot.GetRotation().GetAxisZ().GetSafeNormal2D();
	}
	if (Out.IsNearlyZero())
	{
		Out = -GetActorForwardVector().GetSafeNormal2D();
	}

	DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);

	FVector Velocity;
	FVector Facing;
	if (bWasAttached)
	{
		// flung off beside the player, landing on the ground facing them
		const FVector PlayerLoc = Player->GetActorLocation();
		FVector Pos = PlayerLoc + Out * (Player->GetSimpleCollisionRadius() + LeechRadius + 20.f);
		Pos.Z = FMath::Max(GetActorLocation().Z, PlayerLoc.Z - Player->GetSimpleCollisionHalfHeight() + LeechHalfHeight + 20.f);
		SetActorLocation(Pos);
		Velocity = bThrown ? Out * ShakeOffThrowSpeed + FVector(0.f, 0.f, 250.f) : Out * 120.f;
		Facing = -Out;
	}
	else
	{
		// missed leap: keeps flying past and drops
		Velocity = LeapDir * 250.f + FVector(0.f, 0.f, 60.f);
		Facing = LeapDir.IsNearlyZero() ? GetActorForwardVector() : LeapDir;
	}
	SetActorRotation(FRotator(0.f, Facing.Rotation().Yaw, 0.f));

	SetGroundMode(true);
	GetCharacterMovement()->Velocity = Velocity;

	AttachedPlayer.Reset();
	ShakeCount = 0;
	bShakenOff = bThrown;
	RecoverDuration = MissRecoverTime;
	SetPhase(ELeechPhase::Recovering);

	if (GEngine && bShowShakeOffHint)
	{
		GEngine->RemoveOnScreenDebugMessage(static_cast<uint64>(GetUniqueID()) + 0x1EEC0000ull);
		if (bThrown)
		{
			GEngine->AddOnScreenDebugMessage(-1, 1.2f, FColor(120, 255, 120), TEXT("Pulled the leech off!"), true, FVector2D(2.f, 2.f));
		}
		else if (!bWasAttached)
		{
			GEngine->AddOnScreenDebugMessage(-1, 1.2f, FColor::Cyan, TEXT("Dodged the leech"), true, FVector2D(2.f, 2.f));
		}
	}
}

void AEnemyLeech::ShowHint() const
{
	if (!GEngine || !bShowShakeOffHint)
	{
		return;
	}
	// one line per leech, refreshed every frame while attached
	GEngine->AddOnScreenDebugMessage(static_cast<uint64>(GetUniqueID()) + 0x1EEC0000ull, 0.2f, FColor(255, 70, 70),
		FString::Printf(TEXT("A leech is draining you!  Press E to pull it off  (%d/%d)"), ShakeCount, ShakeOffPresses), true, FVector2D(1.8f, 1.8f));
}

void AEnemyLeech::UpdateBody(float DeltaSeconds, float Now)
{
	const float PhaseTime = Now - PhaseStartTime;

	float Wiggle = 1.2f;		// side-to-side undulation (cm)
	float WiggleSpeed = 2.f;
	float HeadLift = 0.f;		// head raised (cm)
	float Stretch = 1.f;		// body length
	float Swell = 1.f;			// body thickness

	switch (Phase)
	{
	case ELeechPhase::Resting:
		if (State == EEnemyState::Chase)
		{
			// sniffing the air
			HeadLift = 4.f + 2.f * FMath::Sin(Now * 3.f);
			WiggleSpeed = 3.f;
		}
		break;

	case ELeechPhase::WindUp:
	{
		// rears up and bunches together, quivering
		const float A = FMath::Clamp(PhaseTime / FMath::Max(WindUpTime, 0.01f), 0.f, 1.f);
		HeadLift = 4.f + 12.f * A;
		Stretch = 1.f - 0.2f * A;
		Swell = 1.f + 0.1f * A;
		Wiggle = 0.8f;
		WiggleSpeed = 25.f;
		break;
	}

	case ELeechPhase::Leaping:
		Stretch = 1.25f;
		Swell = 0.9f;
		Wiggle = 0.f;
		break;

	case ELeechPhase::Attached:
		// gulping, swelling up as it drinks; jerks when the player tugs at it
		Wiggle = 1.f;
		WiggleSpeed = 6.f;
		Swell = 1.f + 0.35f * FMath::Clamp(DrunkAmount / 25.f, 0.f, 1.f) + 0.06f * FMath::Sin(Now * 7.f);
		if (Now - LastShakeTime < 0.15f)
		{
			Wiggle = 3.5f;
			WiggleSpeed = 40.f;
			Stretch = 1.15f;
		}
		break;

	case ELeechPhase::Recovering:
		// writhing on the ground
		Wiggle = 3.5f;
		WiggleSpeed = 9.f;
		break;
	}

	if (State == EEnemyState::Dead)
	{
		Wiggle = 0.f;
		HeadLift = 0.f;
	}

	for (int32 i = 0; i < Segments.Num() && i < SegmentBaseLocations.Num(); ++i)
	{
		FVector Loc = SegmentBaseLocations[i];
		Loc.X *= Stretch;
		Loc.Y += Wiggle * FMath::Sin(Now * WiggleSpeed + i * 0.9f) * (0.4f + 0.6f * i / FMath::Max(Segments.Num() - 1, 1));
		const float HeadPart = FMath::Max(0.f, 1.f - i / 3.f);
		Loc.Z += HeadLift * HeadPart * HeadPart;
		Segments[i]->SetRelativeLocation(Loc);

		FVector Scale = SegmentBaseScales[i];
		Scale.Y *= Swell;
		Scale.Z *= Swell;
		Segments[i]->SetRelativeScale3D(Scale);
	}
	if (Segments.Num() > 0)
	{
		Mouth->SetRelativeLocation(Segments[0]->GetRelativeLocation() + FVector(3.5f, 0.f, -0.5f));
	}

	// dead: flattens out and sinks
	float Flatten = 1.f;
	float Sink = 0.f;
	if (State == EEnemyState::Dead && DeathTime >= 0.f)
	{
		const float T = FMath::Clamp((Now - DeathTime) / 0.8f, 0.f, 1.f);
		Flatten = 1.f - 0.65f * T;
		Sink = 3.f * T;
	}
	BodyRoot->SetRelativeScale3D(FVector(1.f + 0.15f * (1.f - Flatten), 1.f + 0.15f * (1.f - Flatten), Flatten));
	BodyRoot->SetRelativeLocation(FVector(0.f, 0.f, -LeechHalfHeight - Sink));
}

void AEnemyLeech::ResetEnemy()
{
	if (GEngine)
	{
		GEngine->RemoveOnScreenDebugMessage(static_cast<uint64>(GetUniqueID()) + 0x1EEC0000ull);
	}
	DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
	AttachedPlayer.Reset();

	Super::ResetEnemy();

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->MaxWalkSpeed = 0.f;
	Movement->bOrientRotationToMovement = false;
	Tags.Remove(TEXT("LockOnTarget"));

	DeathTime = -1.f;
	bShakenOff = false;
	ShakeCount = 0;
	DrunkAmount = 0.f;
	NextLatchTime = 0.f;
	SetPhase(ELeechPhase::Resting);
	BodyRoot->SetRelativeScale3D(FVector::OneVector);
	BodyRoot->SetRelativeLocation(FVector(0.f, 0.f, -LeechHalfHeight));
}
