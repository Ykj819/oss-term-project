// Withered tree enemy: never moves. A thin white mist always hangs at its roots; when it notices the player
// the mist swells into a wide fog that drains health continuously (blocking / rolling don't help - kill the tree or get out)

#include "EnemyFogTree.h"
#include "StatsComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Math/RandomStream.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr float TreeHalfHeight = 190.f;
	constexpr int32 NumPuffs = 26;
}

AEnemyFogTree::AEnemyFogTree()
{
	GetCapsuleComponent()->InitCapsuleSize(45.f, TreeHalfHeight);

	// no body: the mannequin from the base class is removed
	GetMesh()->SetSkeletalMeshAsset(nullptr);
	GetMesh()->SetAnimInstanceClass(nullptr);
	GetMesh()->SetVisibility(false);
	GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	AttackAnimations.Reset();
	HeavyAttackAnimation.Reset();
	HitReactAnimation.Reset();

	// rooted to the spot
	ChaseSpeed = 0.f;
	GetCharacterMovement()->MaxWalkSpeed = 0.f;
	GetCharacterMovement()->bOrientRotationToMovement = false;

	SightRange = 1300.f;
	LoseSightRange = 1800.f;
	SoulReward = 25;
	HealthBarHeight = 230.f;
	HealthBarSize = FVector2D(110.f, 8.f);
	bFlinchOnHit = false;
	BaseEyeHeight = 120.f;

	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphereMesh(TEXT("/Engine/BasicShapes/Sphere.Sphere"));

	// ---- tree (origin at the ground under the capsule) ----
	TreeRoot = CreateDefaultSubobject<USceneComponent>(TEXT("TreeRoot"));
	TreeRoot->SetupAttachment(RootComponent);
	TreeRoot->SetRelativeLocation(FVector(0.f, 0.f, -TreeHalfHeight));

	// one mesh: trunk, roots and bare branches as a single smooth surface with the realistic bark texture
	// (Export/Blender/scripts/props/gen_enemy_props.py, same layout as the old engine-shape tree; origin = ground)
	static ConstructorHelpers::FObjectFinder<UStaticMesh> TreeMesh(TEXT("/Game/Characters/Enemies/Meshes/SM_FogTree.SM_FogTree"));
	UStaticMeshComponent* Wood = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Wood"));
	Wood->SetupAttachment(TreeRoot);
	Wood->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Wood->SetGenerateOverlapEvents(false);
	Wood->SetCanEverAffectNavigation(false);
	if (TreeMesh.Succeeded())
	{
		Wood->SetStaticMesh(TreeMesh.Object);
	}
	TreeParts.Add(Wood);
	// ---- fog puffs (flattened spheres drifting around the trunk; M_EnemyFog: soft edges, drifting noise, depth fade) ----
	FogRoot = CreateDefaultSubobject<USceneComponent>(TEXT("FogRoot"));
	FogRoot->SetupAttachment(RootComponent);
	FogRoot->SetUsingAbsoluteRotation(true);
	FogRoot->SetRelativeLocation(FVector(0.f, 0.f, -TreeHalfHeight));

	static ConstructorHelpers::FObjectFinder<UMaterialInterface> FogMat(TEXT("/Game/Characters/Enemies/Materials/M_EnemyFog.M_EnemyFog"));
	for (int32 i = 0; i < NumPuffs; ++i)
	{
		UStaticMeshComponent* Puff = CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("FogPuff%d"), i));
		Puff->SetupAttachment(FogRoot);
		Puff->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Puff->SetGenerateOverlapEvents(false);
		Puff->SetCanEverAffectNavigation(false);
		Puff->SetCastShadow(false);
		Puff->SetHiddenInGame(true);
		if (SphereMesh.Succeeded())
		{
			Puff->SetStaticMesh(SphereMesh.Object);
		}
		if (FogMat.Succeeded())
		{
			Puff->SetMaterial(0, FogMat.Object);
		}
		FogPuffs.Add(Puff);
	}
}

void AEnemyFogTree::BeginPlay()
{
	Super::BeginPlay();

	if (UStatsComponent* EnemyStats = FindComponentByClass<UStatsComponent>())
	{
		EnemyStats->SetMaxHealth(MaxHealth);
		EnemyStats->RestoreAll();
	}
	GetCharacterMovement()->MaxWalkSpeed = 0.f;

	// placed actors saved this array when it held the old engine-shape parts (now deleted -> null entries): rebuild it
	TreeParts.Reset();
	{
		TInlineComponentArray<UStaticMeshComponent*> Comps(this);
		for (UStaticMeshComponent* Comp : Comps)
		{
			if (Comp && Comp->GetFName() == TEXT("Wood"))
			{
				TreeParts.Add(Comp);
			}
		}
	}

	for (UStaticMeshComponent* Part : TreeParts)
	{
		if (UMaterialInstanceDynamic* MID = Part->CreateDynamicMaterialInstance(0))
		{
			MID->SetVectorParameterValue(TEXT("Color"), BarkColor);
		}
	}

	// one shared material for all puffs (their alpha moves together)
	if (FogPuffs.Num() > 0)
	{
		if (UMaterialInterface* Base = FogPuffs[0]->GetMaterial(0))
		{
			FogMaterial = UMaterialInstanceDynamic::Create(Base, this);
			for (UStaticMeshComponent* Puff : FogPuffs)
			{
				Puff->SetMaterial(0, FogMaterial);
			}
		}
	}

	// puffs spread over the disc: denser near the trunk, a few out at the edge
	Puffs.Reset();
	for (int32 i = 0; i < FogPuffs.Num(); ++i)
	{
		FPuff P;
		P.Angle = FMath::FRandRange(0.f, 2.f * PI);
		P.RadiusFrac = FMath::Sqrt(FMath::FRandRange(0.02f, 1.f)) * 0.85f;
		P.Height = FMath::FRandRange(0.05f, 0.6f);
		P.Size = FMath::FRandRange(0.45f, 0.75f);
		P.Drift = FMath::FRandRange(0.08f, 0.25f) * (FMath::RandBool() ? 1.f : -1.f);
		P.Phase = FMath::FRandRange(0.f, 2.f * PI);
		Puffs.Add(P);
	}

	FogAmount = IdleFogFraction;
}

float AEnemyFogTree::GroundZ() const
{
	return GetActorLocation().Z - GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
}

void AEnemyFogTree::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	const float Now = GetWorld()->GetTimeSeconds();

	// dead: tips over and sinks, the fog dies away
	if (State == EEnemyState::Dead)
	{
		if (DeathTime < 0.f)
		{
			DeathTime = Now;
			const float Yaw = FMath::FRandRange(0.f, 2.f * PI);
			FallAxis = FVector(FMath::Cos(Yaw), FMath::Sin(Yaw), 0.f);
		}
		const float T = FMath::Clamp((Now - DeathTime) / 1.4f, 0.f, 1.f);
		const float Fall = T * T;	// slow start, crashes down
		TreeRoot->SetWorldRotation(FQuat(FallAxis, FMath::DegreesToRadians(80.f * Fall)) * GetActorQuat());
		TreeRoot->SetRelativeLocation(FVector(0.f, 0.f, -TreeHalfHeight - 60.f * FMath::Clamp((Now - DeathTime - 1.4f) / 3.f, 0.f, 1.f)));
	}

	UpdateFog(DeltaSeconds, Now);
	DamagePlayerInFog(DeltaSeconds);
}

void AEnemyFogTree::TickCombat(APawn* Player, float Distance, float Now, float DeltaSeconds)
{
	// never moves or attacks: the fog (in Tick) is the attack. Only calms down when the player is far away
	if (Distance > LoseSightRange)
	{
		State = EEnemyState::Idle;
	}
}

void AEnemyFogTree::UpdateFog(float DeltaSeconds, float Now)
{
	// awake = full fog, calm = thin mist at the roots, dead = nothing
	float Target = IdleFogFraction;
	if (State == EEnemyState::Dead)
	{
		Target = 0.f;
	}
	else if (State == EEnemyState::Chase || State == EEnemyState::Attack)
	{
		Target = 1.f;
	}
	FogAmount = FMath::FInterpConstantTo(FogAmount, Target, DeltaSeconds, 1.f / FMath::Max(FogSpreadTime, 0.1f));

	const bool bVisible = FogAmount > 0.01f;
	const float Radius = FogRadius * FogAmount;
	for (int32 i = 0; i < FogPuffs.Num() && i < Puffs.Num(); ++i)
	{
		UStaticMeshComponent* Puff = FogPuffs[i];
		Puff->SetHiddenInGame(!bVisible);
		if (!bVisible)
		{
			continue;
		}

		FPuff& P = Puffs[i];
		P.Angle += P.Drift * DeltaSeconds;
		const float Breathe = 1.f + 0.12f * FMath::Sin(Now * 0.7f + P.Phase);
		const float R = Radius * P.RadiusFrac;
		const FVector Pos(FMath::Cos(P.Angle) * R, FMath::Sin(P.Angle) * R, FogHeight * P.Height * FMath::Max(FogAmount, 0.4f));

		// wide and flat, at least big enough to wrap the trunk (engine sphere is 100 wide)
		const float Width = FMath::Max(Radius * P.Size, 120.f) * Breathe;
		const float Height = FMath::Max(FogHeight * 0.55f * P.Size * FMath::Max(FogAmount, 0.5f), 60.f) * Breathe;
		Puff->SetRelativeLocation(Pos);
		Puff->SetRelativeScale3D(FVector(Width / 100.f, Width * 0.8f / 100.f, Height / 100.f));
		Puff->SetRelativeRotation(FRotator(0.f, FMath::RadiansToDegrees(P.Angle) + P.Phase * 30.f, 0.f));
	}

	if (FogMaterial)
	{
		// thinner while it spreads, fades as it dies
		FLinearColor Color = FogColor;
		Color.A = FogColor.A * FMath::Clamp(FogAmount * 2.f, 0.f, 1.f);
		FogMaterial->SetVectorParameterValue(TEXT("Color"), Color);
	}
}

void AEnemyFogTree::DamagePlayerInFog(float DeltaSeconds)
{
	FogDamageTimer += DeltaSeconds;
	if (FogDamageTimer < FogDamageInterval)
	{
		return;
	}
	FogDamageTimer = 0.f;

	if (FogAmount <= 0.01f || State == EEnemyState::Dead)
	{
		return;
	}

	APawn* Player = GetPlayer();
	if (!Player)
	{
		return;
	}

	// inside the fog disc and not high above it
	const FVector P = Player->GetActorLocation();
	const float Feet = P.Z - Player->GetSimpleCollisionHalfHeight() - GroundZ();
	if (FVector::Dist2D(P, GetActorLocation()) > FogRadius * FogAmount || Feet > FogHeight || Feet < -150.f)
	{
		return;
	}

	// straight to health: a guard or a roll doesn't keep fog out, and it doesn't make the player flinch every tick
	if (UStatsComponent* PlayerStats = Player->FindComponentByClass<UStatsComponent>())
	{
		PlayerStats->ApplyDamage(FogDamagePerSecond * FogDamageInterval, this);
	}

	// breathing it in wakes the tree up
	if (State == EEnemyState::Idle)
	{
		State = EEnemyState::Chase;
	}
}

void AEnemyFogTree::ResetEnemy()
{
	Super::ResetEnemy();

	GetCharacterMovement()->MaxWalkSpeed = 0.f;
	GetCharacterMovement()->bOrientRotationToMovement = false;
	DeathTime = -1.f;
	TreeRoot->SetRelativeRotation(FRotator::ZeroRotator);
	TreeRoot->SetRelativeLocation(FVector(0.f, 0.f, -TreeHalfHeight));
	FogAmount = IdleFogFraction;
	FogDamageTimer = 0.f;
}
