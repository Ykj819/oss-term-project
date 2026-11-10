// Temporary enemy stand-in: a sphere the player can lock on to

#include "LockOnDummy.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/Pawn.h"
#include "TimerManager.h"

ALockOnDummy::ALockOnDummy()
{
	PrimaryActorTick.bCanEverTick = false;

	Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
	RootComponent = Body;
	Body->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	Body->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphereMesh(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	if (SphereMesh.Succeeded())
	{
		Body->SetStaticMesh(SphereMesh.Object);
	}

	// the player's lock-on looks for this tag
	Tags.Add(TEXT("LockOnTarget"));
}

void ALockOnDummy::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);

	// engine sphere is 100cm across
	Body->SetRelativeScale3D(FVector(Diameter / 100.f));
}

void ALockOnDummy::BeginPlay()
{
	Super::BeginPlay();

	BodyMaterial = Body->CreateDynamicMaterialInstance(0);
	if (BodyMaterial)
	{
		BodyMaterial->SetVectorParameterValue(TEXT("Color"), Color);
	}

	if (bAttackPlayer)
	{
		GetWorldTimerManager().SetTimer(AttackLoopTimer, this, &ALockOnDummy::StartAttack, AttackInterval, true, AttackInterval);
	}
}

APawn* ALockOnDummy::GetPlayerInRange() const
{
	APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!Player)
	{
		return nullptr;
	}

	const float Distance = FVector::Dist(Player->GetActorLocation(), GetActorLocation()) - Diameter * 0.5f;
	return Distance <= AttackRange ? Player : nullptr;
}

void ALockOnDummy::StartAttack()
{
	if (!GetPlayerInRange() || GetWorldTimerManager().IsTimerActive(AttackHitTimer))
	{
		return;
	}

	// wind-up: glow so the player can time the dodge / block
	if (BodyMaterial)
	{
		BodyMaterial->SetVectorParameterValue(TEXT("Color"), WindupColor);
	}
	GetWorldTimerManager().SetTimer(AttackHitTimer, this, &ALockOnDummy::LandAttack, AttackWindup, false);
}

void ALockOnDummy::LandAttack()
{
	if (BodyMaterial)
	{
		BodyMaterial->SetVectorParameterValue(TEXT("Color"), Color);
	}

	if (APawn* Player = GetPlayerInRange())
	{
		UGameplayStatics::ApplyDamage(Player, AttackDamage, nullptr, this, UDamageType::StaticClass());
	}
}
