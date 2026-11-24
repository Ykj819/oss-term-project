// Death "poof" smoke, see DeathSmoke.h

#include "DeathSmoke.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Camera/PlayerCameraManager.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

ADeathSmoke::ADeathSmoke()
{
	PrimaryActorTick.bCanEverTick = true;

	Puffs = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Puffs"));
	RootComponent = Puffs;
	Puffs->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Puffs->SetGenerateOverlapEvents(false);
	Puffs->SetCastShadow(false);
	Puffs->SetCanEverAffectNavigation(false);
	Puffs->SetUsingAbsoluteLocation(true);
	Puffs->SetUsingAbsoluteRotation(true);
	Puffs->SetUsingAbsoluteScale(true);
	Puffs->NumCustomDataFloats = 2;

	// engine plane: 100 x 100 cm in XY, facing +Z
	static ConstructorHelpers::FObjectFinder<UStaticMesh> PlaneMesh(TEXT("/Engine/BasicShapes/Plane.Plane"));
	if (PlaneMesh.Succeeded())
	{
		Puffs->SetStaticMesh(PlaneMesh.Object);
	}
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> SmokeMat(TEXT("/Game/Effects/DeathSmoke/M_DeathSmoke.M_DeathSmoke"));
	if (SmokeMat.Succeeded())
	{
		Puffs->SetMaterial(0, SmokeMat.Object);
	}
}

ADeathSmoke* ADeathSmoke::Poof(AActor* Dead)
{
	if (!Dead || !Dead->GetWorld())
	{
		return nullptr;
	}

	// smoke sized from the body while it is still visible
	ADeathSmoke* Smoke = Burst(Dead);

	// gone at once
	TInlineComponentArray<USkeletalMeshComponent*> Skels(Dead);
	for (USkeletalMeshComponent* Skel : Skels)
	{
		Skel->SetSimulatePhysics(false);
		Skel->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	}
	Dead->SetActorHiddenInGame(true);
	return Smoke;
}

ADeathSmoke* ADeathSmoke::Burst(AActor* Target)
{
	if (!Target || !Target->GetWorld())
	{
		return nullptr;
	}
	AActor* Dead = Target;

	// the visible body: meshes that are shown (not health bars, markers, fog, leaf storms, ...)
	FBox Body(ForceInit);
	TInlineComponentArray<UPrimitiveComponent*> Prims(Dead);
	for (UPrimitiveComponent* Prim : Prims)
	{
		if (!Prim || !Prim->IsRegistered() || !Prim->IsVisible() || Prim->bHiddenInGame || Prim->IsA<UInstancedStaticMeshComponent>())
		{
			continue;
		}
		if (!Prim->IsA<UStaticMeshComponent>() && !Prim->IsA<USkeletalMeshComponent>())
		{
			continue;
		}
		const FString Name = Prim->GetName();
		if (Name.StartsWith(TEXT("HealthBar")) || Name.StartsWith(TEXT("LockOn")) || Name.StartsWith(TEXT("FogPuff")))
		{
			continue;
		}
		Body += Prim->Bounds.GetBox();
	}
	if (!Body.IsValid)
	{
		Body = FBox::BuildAABB(Dead->GetActorLocation(), FVector(40.f, 40.f, 90.f));
	}

	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ADeathSmoke* Smoke = Dead->GetWorld()->SpawnActor<ADeathSmoke>(ADeathSmoke::StaticClass(), FTransform(Body.GetCenter()), Params);
	if (Smoke)
	{
		Smoke->Start(Body);
	}
	return Smoke;
}

void ADeathSmoke::Start(const FBox& Body)
{
	const FVector Center = Body.GetCenter();
	const FVector Extent = Body.GetExtent().ComponentMax(FVector(15.f));
	const float HalfWidth = FMath::Max(Extent.X, Extent.Y);

	// more puffs for bigger bodies (mannequin ~ 45 x 45 x 90 half extents = 1x)
	const float Volume = (Extent.X * Extent.Y * Extent.Z) / (45.f * 45.f * 90.f);
	const int32 Count = FMath::Clamp(FMath::RoundToInt(BasePuffs * FMath::Pow(Volume, 0.45f)), 5, MaxPuffs);
	const float Size = FMath::Clamp(FMath::Min(HalfWidth * 1.6f, Extent.Z * 1.1f), 35.f, 600.f) * PuffSizeScale;

	PuffData.SetNum(Count);
	TArray<FTransform> Transforms;
	Transforms.Reserve(Count);
	for (FPuff& P : PuffData)
	{
		// inside the body, a bit more at the bottom; pushed outward and up
		const FVector Dir = FMath::VRand();
		const FVector Local(Dir.X * Extent.X * 0.6f, Dir.Y * Extent.Y * 0.6f, Dir.Z * Extent.Z * 0.75f);
		P.Position = Center + Local * FMath::FRandRange(0.2f, 1.f);
		FVector Out = Local.GetSafeNormal();
		Out.Z = FMath::Abs(Out.Z) * 0.5f;
		// the flipbook already bursts outward: the cards only drift apart a little
		P.Velocity = Out * FMath::FRandRange(0.5f, 1.f) * Size * 0.35f + FVector(0.f, 0.f, Size * FMath::FRandRange(0.1f, 0.25f));
		// one card holds a whole burst (tiny at frame 0, filling ~70% of the card at the end)
		P.StartSize = Size * FMath::FRandRange(2.f, 2.6f);
		P.EndSize = P.StartSize * FMath::FRandRange(1.1f, 1.3f);
		P.Life = Duration * FMath::FRandRange(0.8f, 1.2f);
		P.Delay = FMath::FRandRange(0.f, 0.08f);
		P.Roll = FMath::FRandRange(0.f, 2.f * PI);
		P.RollSpeed = FMath::FRandRange(-1.2f, 1.2f);
		Transforms.Add(FTransform(FQuat::Identity, P.Position, FVector(0.001f)));
	}
	Puffs->AddInstances(Transforms, false, true);
	for (int32 i = 0; i < Count; ++i)
	{
		Puffs->SetCustomDataValue(i, 0, 0.f, false);
		Puffs->SetCustomDataValue(i, 1, 0.f, false);
	}
	Puffs->MarkRenderStateDirty();
}

void ADeathSmoke::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Age += DeltaSeconds;

	FVector CamLoc = GetActorLocation() + FVector(-1000.f, 0.f, 0.f);
	if (APlayerCameraManager* Cam = UGameplayStatics::GetPlayerCameraManager(this, 0))
	{
		CamLoc = Cam->GetCameraLocation();
	}

	bool bAlive = false;
	TArray<FTransform> Transforms;
	Transforms.SetNum(PuffData.Num());
	for (int32 i = 0; i < PuffData.Num(); ++i)
	{
		FPuff& P = PuffData[i];
		const float T = FMath::Clamp((Age - P.Delay) / P.Life, 0.f, 1.f);
		if (Age - P.Delay < P.Life)
		{
			bAlive = true;
		}
		if (Age > P.Delay)
		{
			// fast burst that slows down (drag), keeps rising a little
			P.Position += P.Velocity * DeltaSeconds;
			P.Velocity *= FMath::Exp(-3.2f * DeltaSeconds);
			P.Velocity.Z += 25.f * DeltaSeconds;
			P.Roll += P.RollSpeed * DeltaSeconds;
		}
		const float Grow = 1.f - FMath::Pow(1.f - T, 2.5f);			// ease out
		const float Scale = FMath::Lerp(P.StartSize, P.EndSize, Grow) / 100.f;
		const FVector ToCam = (CamLoc - P.Position).GetSafeNormal();
		const FQuat Facing = FRotationMatrix::MakeFromZ(ToCam).ToQuat() * FQuat(FVector::UpVector, P.Roll);
		Transforms[i] = FTransform(Facing, P.Position, FVector(Age > P.Delay ? Scale : 0.001f));

		const float FadeIn = FMath::Clamp(T / 0.06f, 0.f, 1.f);
		const float FadeOut = 1.f - FMath::SmoothStep(0.6f, 1.f, T);
		Puffs->SetCustomDataValue(i, 0, T * 63.f, false);	// 8 x 8 flipbook
		Puffs->SetCustomDataValue(i, 1, FadeIn * FadeOut, false);
	}
	Puffs->BatchUpdateInstancesTransforms(0, Transforms, true, true, false);

	if (!bAlive)
	{
		Destroy();
	}
}
