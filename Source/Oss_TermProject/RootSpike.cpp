// Root spike for the tree boss.

#include "RootSpike.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Character.h"
#include "GameFramework/DamageType.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr float RiseTime = 0.12f;
	constexpr float HoldTime = 1.0f;
	constexpr float SinkTime = 0.5f;
	constexpr float HitTime = 0.35f;	// the spikes hurt for this long after bursting up
	constexpr int32 NumSpikes = 5;

	UStaticMeshComponent* MakePart(AActor* Owner, const TCHAR* Name, UStaticMesh* Mesh, USceneComponent* Parent)
	{
		UStaticMeshComponent* Part = Owner->CreateDefaultSubobject<UStaticMeshComponent>(Name);
		Part->SetupAttachment(Parent);
		Part->SetStaticMesh(Mesh);
		Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Part->SetGenerateOverlapEvents(false);
		Part->SetCanEverAffectNavigation(false);
		return Part;
	}
}

ARootSpike::ARootSpike()
{
	PrimaryActorTick.bCanEverTick = true;

	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));

	static ConstructorHelpers::FObjectFinder<UStaticMesh> CylinderMesh(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> ConeMesh(TEXT("/Engine/BasicShapes/Cone.Cone"));

	Warning = MakePart(this, TEXT("Warning"), CylinderMesh.Object, RootComponent);
	Warning->SetCastShadow(false);

	for (int32 i = 0; i < NumSpikes; ++i)
	{
		UStaticMeshComponent* Spike = MakePart(this, *FString::Printf(TEXT("Spike%d"), i), ConeMesh.Object, RootComponent);
		Spike->SetHiddenInGame(true);
		Spikes.Add(Spike);
	}
}

void ARootSpike::BeginPlay()
{
	Super::BeginPlay();

	// warning disc (engine cylinder: 100 wide, 100 tall, centered)
	Warning->SetRelativeScale3D(FVector(Radius / 50.f, Radius / 50.f, 0.03f));
	Warning->SetRelativeLocation(FVector(0.f, 0.f, 3.f));
	WarningMaterial = Warning->CreateDynamicMaterialInstance(0);
	if (WarningMaterial)
	{
		WarningMaterial->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.35f, 0.06f, 0.01f));
	}

	// one tall spike in the middle, smaller ones leaning out around it (engine cone: 100 wide, 100 tall, centered, points +Z)
	SpikeTargets.Reset();
	for (int32 i = 0; i < Spikes.Num(); ++i)
	{
		FTransform T;
		if (i == 0)
		{
			T = FTransform(FRotator::ZeroRotator, FVector(0.f, 0.f, Height * 0.5f - 15.f), FVector(0.9f, 0.9f, Height / 100.f));
		}
		else
		{
			const float Angle = (i - 1) * 90.f + FMath::FRandRange(-20.f, 20.f);
			const FVector Dir = FRotator(0.f, Angle, 0.f).Vector();
			const float H = Height * FMath::FRandRange(0.5f, 0.7f);
			const FRotator Lean = FRotationMatrix::MakeFromZX(FVector::UpVector + Dir * 0.45f, Dir).Rotator();
			T = FTransform(Lean, Dir * Radius * 0.45f + FVector(0.f, 0.f, H * 0.5f - 15.f), FVector(0.6f, 0.6f, H / 100.f));
		}
		SpikeTargets.Add(T);

		if (UMaterialInstanceDynamic* M = Spikes[i]->CreateDynamicMaterialInstance(0))
		{
			M->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.16f, 0.09f, 0.04f));
		}
	}
}

void ARootSpike::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Age += DeltaSeconds;

	if (Age < WarnTime)
	{
		// the circle brightens and pulses faster as the spikes get close
		const float T = Age / WarnTime;
		const float Pulse = 0.5f + 0.5f * FMath::Sin(Age * (8.f + 22.f * T));
		if (WarningMaterial)
		{
			WarningMaterial->SetVectorParameterValue(TEXT("Color"), FMath::Lerp(FLinearColor(0.35f, 0.06f, 0.01f), FLinearColor(1.f, 0.35f, 0.05f), T * (0.6f + 0.4f * Pulse)));
		}
		return;
	}

	const float SpikeAge = Age - WarnTime;
	float Extent;
	if (SpikeAge < RiseTime)
	{
		Extent = SpikeAge / RiseTime;
	}
	else if (SpikeAge < RiseTime + HoldTime)
	{
		Extent = 1.f;
	}
	else
	{
		Extent = 1.f - (SpikeAge - RiseTime - HoldTime) / SinkTime;
	}

	if (Extent <= 0.f)
	{
		Destroy();
		return;
	}

	Warning->SetHiddenInGame(true);
	for (int32 i = 0; i < Spikes.Num(); ++i)
	{
		FTransform T = SpikeTargets[i];
		const FVector Base = T.GetLocation() - T.GetRotation().GetUpVector() * (T.GetScale3D().Z * 50.f);
		T.SetScale3D(FVector(T.GetScale3D().X, T.GetScale3D().Y, T.GetScale3D().Z * Extent));
		T.SetLocation(Base + T.GetRotation().GetUpVector() * (T.GetScale3D().Z * 50.f));
		Spikes[i]->SetRelativeTransform(T);
		Spikes[i]->SetHiddenInGame(false);
	}

	if (!bHasHit && SpikeAge <= HitTime)
	{
		TryHitPlayer();
	}
}

void ARootSpike::TryHitPlayer()
{
	ACharacter* Player = UGameplayStatics::GetPlayerCharacter(this, 0);
	if (!Player || !Player->CanBeDamaged())
	{
		return;
	}

	const FVector Center = GetActorLocation();
	const FVector P = Player->GetActorLocation();
	const float HalfHeight = Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const float PlayerRadius = Player->GetCapsuleComponent()->GetScaledCapsuleRadius();
	const float Feet = P.Z - HalfHeight - Center.Z;

	if (FVector::Dist2D(Center, P) <= Radius + PlayerRadius * 0.5f && Feet <= Height * 0.6f && Feet >= -100.f)
	{
		bHasHit = true;
		const APawn* OwnerPawn = Cast<APawn>(GetOwner());
		UGameplayStatics::ApplyDamage(Player, Damage, OwnerPawn ? OwnerPawn->GetController() : nullptr, GetOwner() ? GetOwner() : this, UDamageType::StaticClass());
	}
}
