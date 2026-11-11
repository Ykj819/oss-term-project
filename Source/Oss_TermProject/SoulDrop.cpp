// Souls left behind where the player died: walk into it to get them back

#include "SoulDrop.h"
#include "Oss_TermProjectCharacter.h"
#include "StatsComponent.h"
#include "Oss_TermProject.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

ASoulDrop::ASoulDrop()
{
	PrimaryActorTick.bCanEverTick = false;

	PickupSphere = CreateDefaultSubobject<USphereComponent>(TEXT("PickupSphere"));
	RootComponent = PickupSphere;
	PickupSphere->InitSphereRadius(100.f);
	PickupSphere->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
	PickupSphere->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	PickupSphere->SetCollisionResponseToAllChannels(ECR_Ignore);
	PickupSphere->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
	PickupSphere->SetGenerateOverlapEvents(true);

	Orb = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Orb"));
	Orb->SetupAttachment(PickupSphere);
	Orb->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Orb->SetCastShadow(false);
	Orb->SetRelativeScale3D(FVector(0.25f));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphereMesh(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	if (SphereMesh.Succeeded())
	{
		Orb->SetStaticMesh(SphereMesh.Object);
	}

	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));
	Glow->SetupAttachment(PickupSphere);
	Glow->SetIntensity(4000.f);
	Glow->SetAttenuationRadius(400.f);
	Glow->SetCastShadows(false);
}

ASoulDrop* ASoulDrop::SpawnAt(UObject* WorldContext, const FVector& Location, int32 InAmount)
{
	UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (!World || InAmount <= 0)
	{
		return nullptr;
	}

	// on the ground below the death spot, orb floating at waist height
	FVector Spot = Location;
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(SoulDropGround), false, Cast<AActor>(WorldContext));
	if (World->LineTraceSingleByChannel(Hit, Location, Location - FVector(0.f, 0.f, 2000.f), ECC_Visibility, Params))
	{
		Spot = Hit.ImpactPoint;
	}
	Spot.Z += 50.f;

	FActorSpawnParameters SpawnParams;
	SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ASoulDrop* Drop = World->SpawnActor<ASoulDrop>(ASoulDrop::StaticClass(), Spot, FRotator::ZeroRotator, SpawnParams);
	if (Drop)
	{
		Drop->Amount = InAmount;
	}
	return Drop;
}

void ASoulDrop::BeginPlay()
{
	Super::BeginPlay();

	if (UMaterialInstanceDynamic* MID = Orb->CreateDynamicMaterialInstance(0))
	{
		MID->SetVectorParameterValue(TEXT("Color"), Color);
	}
	Glow->SetLightColor(Color);

	PickupSphere->OnComponentBeginOverlap.AddDynamic(this, &ASoulDrop::OnPickupOverlap);
}

void ASoulDrop::OnPickupOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	TryPickup(OtherActor);
}

bool ASoulDrop::TryPickup(AActor* Actor)
{
	AOss_TermProjectCharacter* Player = Cast<AOss_TermProjectCharacter>(Actor);
	if (!Player || !Player->GetStats() || Player->GetStats()->IsDead() || Amount <= 0)
	{
		return false;
	}

	// the player's body must really be close (not just some part of it registering an overlap mid-teleport)
	if (FVector::Dist(Player->GetActorLocation(), GetActorLocation()) > PickupSphere->GetScaledSphereRadius() + 120.f)
	{
		return false;
	}

	Player->AddSouls(Amount);

	if (GEngine)
	{
		GEngine->AddOnScreenDebugMessage(-1, 2.f, Color.ToFColor(true), FString::Printf(TEXT("Souls retrieved: %d"), Amount));
	}
	UE_LOG(LogOss_TermProject, Log, TEXT("'%s' retrieved %d souls"), *GetNameSafe(Player), Amount);

	Amount = 0;
	Destroy();
	return true;
}
