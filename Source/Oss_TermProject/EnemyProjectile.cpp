// Thrown rock: flies in an arc, hurts the player once (blockable, rolls pass through), breaks on walls/ground

#include "EnemyProjectile.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"
#include "Oss_TermProjectCharacter.h"

AEnemyProjectile::AEnemyProjectile()
{
	PrimaryActorTick.bCanEverTick = true;

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	RootComponent = Mesh;
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetGenerateOverlapEvents(false);
	Mesh->SetCanEverAffectNavigation(false);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphereMesh(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	if (SphereMesh.Succeeded())
	{
		Mesh->SetStaticMesh(SphereMesh.Object);
	}
}

void AEnemyProjectile::BeginPlay()
{
	Super::BeginPlay();

	// lumpy rock: engine sphere is 100 wide, squashed a little differently each throw
	const float D = Radius / 50.f;
	Mesh->SetWorldScale3D(FVector(D * FMath::FRandRange(0.9f, 1.15f), D * FMath::FRandRange(0.8f, 1.f), D * FMath::FRandRange(0.7f, 0.9f)));
	if (UMaterialInstanceDynamic* MID = Mesh->CreateDynamicMaterialInstance(0))
	{
		MID->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.09f, 0.08f, 0.07f));
	}
	Spin = FRotator(FMath::FRandRange(-720.f, 720.f), FMath::FRandRange(-360.f, 360.f), FMath::FRandRange(-720.f, 720.f));

	PassThrough.Add(GetOwner());
}

void AEnemyProjectile::Launch(const FVector& InVelocity, float InGravityZ, float InDamage)
{
	Velocity = InVelocity;
	GravityZ = InGravityZ;
	Damage = InDamage;
	bLaunched = true;
}

void AEnemyProjectile::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	if (!bLaunched)
	{
		return;
	}

	Age += DeltaSeconds;
	if (Age > MaxLifeTime)
	{
		Destroy();
		return;
	}

	const FVector Start = GetActorLocation();
	const FVector End = Start + Velocity * DeltaSeconds + FVector(0.f, 0.f, 0.5f * GravityZ * DeltaSeconds * DeltaSeconds);
	Velocity.Z += GravityZ * DeltaSeconds;

	APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(EnemyProjectile), false, this);

	// a few retries: skipping an enemy or a rolling player continues the same sweep
	for (int32 Try = 0; Try < 4; ++Try)
	{
		for (const TWeakObjectPtr<AActor>& Ignored : PassThrough)
		{
			if (Ignored.IsValid())
			{
				Params.AddIgnoredActor(Ignored.Get());
			}
		}

		FHitResult Hit;
		if (!GetWorld()->SweepSingleByChannel(Hit, Start, End, FQuat::Identity, ECC_WorldDynamic, FCollisionShape::MakeSphere(Radius), Params))
		{
			break;
		}

		AActor* HitActor = Hit.GetActor();
		if (HitActor && HitActor->ActorHasTag(TEXT("Enemy")))
		{
			PassThrough.Add(HitActor);
			continue;
		}

		if (HitActor && HitActor == Player)
		{
			// rolled through it: the rock keeps flying
			if (const AOss_TermProjectCharacter* PlayerCharacter = Cast<AOss_TermProjectCharacter>(Player))
			{
				if (PlayerCharacter->IsDodging())
				{
					PassThrough.Add(Player);
					continue;
				}
			}

			// the thrower is the damage causer, so blocking works when facing the thrower (where the rock came from)
			AActor* Causer = GetOwner() ? GetOwner() : this;
			const APawn* OwnerPawn = Cast<APawn>(GetOwner());
			UGameplayStatics::ApplyDamage(Player, Damage, OwnerPawn ? OwnerPawn->GetController() : nullptr, Causer, UDamageType::StaticClass());
		}

		SetActorLocation(Hit.Location);
		Break();
		return;
	}

	SetActorLocation(End);
	Mesh->AddLocalRotation(Spin * DeltaSeconds);
}

void AEnemyProjectile::Break()
{
	Destroy();
}
