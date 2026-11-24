// One-way boss fog gate, see FogGate.h

#include "FogGate.h"
#include "FishmanBoss.h"
#include "WolfBoss.h"
#include "TreeBoss.h"
#include "Components/ArrowComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Character.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr int32 NumLayers = 3;
	constexpr float LayerSpacing = 8.f;		// cm between the fog planes (depth)
}

AFogGate::AFogGate()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickInterval = 0.f;

	// origin = bottom centre of the gate on the floor
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;

	Blocker = CreateDefaultSubobject<UBoxComponent>(TEXT("Blocker"));
	Blocker->SetupAttachment(Root);
	Blocker->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	Blocker->SetCollisionObjectType(ECC_WorldStatic);
	Blocker->SetCollisionResponseToAllChannels(ECR_Ignore);
	Blocker->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
	Blocker->SetCollisionResponseToChannel(ECC_PhysicsBody, ECR_Block);
	Blocker->SetCanEverAffectNavigation(false);

	PassDirection = CreateDefaultSubobject<UArrowComponent>(TEXT("PassDirection"));
	PassDirection->SetupAttachment(Root);
	PassDirection->SetArrowColor(FLinearColor(0.2f, 0.5f, 1.f));
	PassDirection->ArrowSize = 3.f;

	static ConstructorHelpers::FObjectFinder<UStaticMesh> PlaneMesh(TEXT("/Engine/BasicShapes/Plane.Plane"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> FogMat(TEXT("/Game/Effects/FogGate/M_FogGate.M_FogGate"));
	for (int32 i = 0; i < NumLayers; ++i)
	{
		UStaticMeshComponent* Layer = CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("FogLayer%d"), i));
		Layer->SetupAttachment(Root);
		Layer->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Layer->SetCastShadow(false);
		Layer->SetCanEverAffectNavigation(false);
		if (PlaneMesh.Succeeded())
		{
			Layer->SetStaticMesh(PlaneMesh.Object);
		}
		if (FogMat.Succeeded())
		{
			Layer->SetMaterial(0, FogMat.Object);
		}
		FogLayers.Add(Layer);
	}
}

void AFogGate::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);

	Blocker->SetBoxExtent(FVector(Thickness * 0.5f, Width * 0.5f, Height * 0.5f));
	Blocker->SetRelativeLocation(FVector(0.f, 0.f, Height * 0.5f));
	PassDirection->SetRelativeLocation(FVector(-60.f, 0.f, 100.f));

	// engine plane: 100 x 100 in XY facing +Z; pitch 90 stands it up in the YZ plane (local X -> height)
	for (int32 i = 0; i < FogLayers.Num(); ++i)
	{
		if (UStaticMeshComponent* Layer = FogLayers[i])
		{
			const float Offset = (i - (FogLayers.Num() - 1) * 0.5f) * LayerSpacing;
			Layer->SetRelativeLocationAndRotation(FVector(Offset, 0.f, Height * 0.5f), FRotator(90.f, 0.f, 0.f));
			Layer->SetRelativeScale3D(FVector(Height / 100.f, Width / 100.f, 1.f));
		}
	}
}

void AFogGate::BeginPlay()
{
	Super::BeginPlay();

	// placed actors may load stale entries for this array: rebuild it from the real components
	FogLayers.Reset();
	TInlineComponentArray<UStaticMeshComponent*> Meshes(this);
	for (UStaticMeshComponent* Mesh : Meshes)
	{
		if (Mesh && Mesh->GetName().StartsWith(TEXT("FogLayer")))
		{
			FogLayers.Add(Mesh);
		}
	}

	FogMaterials.Reset();
	for (int32 i = 0; i < FogLayers.Num(); ++i)
	{
		if (UMaterialInstanceDynamic* MID = FogLayers[i]->CreateDynamicMaterialInstance(0))
		{
			MID->SetScalarParameterValue(TEXT("Seed"), 0.37f * i);
			MID->SetScalarParameterValue(TEXT("Speed"), 0.8f + 0.25f * i);
			MID->SetVectorParameterValue(TEXT("Color"), FogColor);
			FogMaterials.Add(MID);
		}
	}

	bHasBoss = Boss != nullptr;
	if (bHasBoss && IsBossDefeated())
	{
		Dissolve();
	}
}

bool AFogGate::IsBossDefeated() const
{
	if (!IsValid(Boss))
	{
		return true;		// destroyed
	}
	if (const AFishmanBoss* Fish = Cast<AFishmanBoss>(Boss))
	{
		return Fish->IsDefeated();
	}
	if (const AWolfBoss* Wolf = Cast<AWolfBoss>(Boss))
	{
		return Wolf->IsDefeated();
	}
	if (const ATreeBoss* Tree = Cast<ATreeBoss>(Boss))
	{
		return Tree->IsDefeated();
	}
	return false;
}

void AFogGate::SetPlayerPassing(ACharacter* Player, bool bPassing)
{
	if (bPlayerPassing == bPassing)
	{
		return;
	}
	bPlayerPassing = bPassing;
	if (UCapsuleComponent* Capsule = Player ? Player->GetCapsuleComponent() : nullptr)
	{
		// the player's movement sweeps ignore the wall while passing; everything else still hits it
		Capsule->IgnoreActorWhenMoving(this, bPassing);
	}
}

void AFogGate::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	ACharacter* Player = UGameplayStatics::GetPlayerCharacter(this, 0);

	if (bDissolving)
	{
		DissolveAlpha = FMath::Min(DissolveAlpha + DeltaSeconds / DissolveTime, 1.f);
		for (UMaterialInstanceDynamic* MID : FogMaterials)
		{
			MID->SetScalarParameterValue(TEXT("Fade"), 1.f - DissolveAlpha);
		}
		if (DissolveAlpha >= 1.f)
		{
			SetPlayerPassing(Player, false);
			SetActorHiddenInGame(true);
			SetActorTickEnabled(false);
		}
		return;
	}

	if (bHasBoss && IsBossDefeated())
	{
		Dissolve();
		return;
	}

	if (!Player)
	{
		return;
	}

	// player position in gate space: X < 0 = entry side (behind the arrow), X > 0 = exit side
	const FVector Local = GetActorTransform().InverseTransformPosition(Player->GetActorLocation());
	const float Radius = Player->GetCapsuleComponent()->GetScaledCapsuleRadius();
	const bool bAtWall = FMath::Abs(Local.X) < Thickness * 0.5f + Radius + 5.f
		&& FMath::Abs(Local.Y) < Width * 0.5f + Radius
		&& Local.Z > -100.f && Local.Z < Height + 100.f;

	// let through when coming from the entry side; keep letting through until the capsule has left the wall,
	// so a player that just crossed isn't pushed back. Approaching from the exit side: blocked.
	const bool bPassing = bAtWall && (Local.X < 0.f || bPlayerPassing);
	SetPlayerPassing(Player, bPassing);
}

void AFogGate::Dissolve()
{
	if (bDissolving)
	{
		return;
	}
	bDissolving = true;
	DissolveAlpha = 0.f;
	Blocker->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	SetActorTickEnabled(true);
}
