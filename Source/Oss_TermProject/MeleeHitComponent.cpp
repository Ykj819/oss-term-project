// Melee hit detection: while a hit window is open, sweeps spheres along weapon segments (stick, fists...) and damages what they touch once per swing

#include "MeleeHitComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "DrawDebugHelpers.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

UMeleeHitComponent::UMeleeHitComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = false;
	// sample after animation has moved the bones this frame
	PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
}

void UMeleeHitComponent::BeginHitWindow(const TArray<FMeleeHitShape>& Shapes, float Damage)
{
	ActiveShapes = Shapes;
	WindowDamage = Damage;
	AlreadyHit.Reset();
	bWindowOpen = ActiveShapes.Num() > 0;

	PreviousPoints.Reset();
	if (bWindowOpen)
	{
		GetPoints(PreviousPoints);
		// catch targets already touching the weapon when the window opens
		SweepAndDamage(PreviousPoints, PreviousPoints);
	}
	SetComponentTickEnabled(bWindowOpen);
}

void UMeleeHitComponent::EndHitWindow()
{
	bWindowOpen = false;
	ActiveShapes.Reset();
	PreviousPoints.Reset();
	SetComponentTickEnabled(false);
}

void UMeleeHitComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	if (!bWindowOpen)
	{
		return;
	}

	TArray<FVector> Points;
	GetPoints(Points);
	if (Points.Num() == PreviousPoints.Num())
	{
		SweepAndDamage(PreviousPoints, Points);
	}
	PreviousPoints = MoveTemp(Points);
}

void UMeleeHitComponent::GetPoints(TArray<FVector>& OutPoints) const
{
	OutPoints.Reset();
	const int32 Samples = FMath::Max(SamplesPerShape, 1);

	for (const FMeleeHitShape& Shape : ActiveShapes)
	{
		if (!Shape.Component)
		{
			for (int32 i = 0; i < Samples; ++i)
			{
				OutPoints.Add(FVector::ZeroVector);
			}
			continue;
		}

		const FTransform Frame = Shape.Socket.IsNone() ? Shape.Component->GetComponentTransform() : Shape.Component->GetSocketTransform(Shape.Socket);
		const FVector A = Frame.TransformPosition(Shape.Start);
		const FVector B = Frame.TransformPosition(Shape.End);
		for (int32 i = 0; i < Samples; ++i)
		{
			OutPoints.Add(Samples == 1 ? A : FMath::Lerp(A, B, float(i) / float(Samples - 1)));
		}
	}
}

void UMeleeHitComponent::SweepAndDamage(const TArray<FVector>& From, const TArray<FVector>& To)
{
	AActor* Owner = GetOwner();
	UWorld* World = GetWorld();
	if (!Owner || !World)
	{
		return;
	}

	FCollisionQueryParams Params(SCENE_QUERY_STAT(MeleeHit), false, Owner);
	FCollisionObjectQueryParams ObjectParams;
	ObjectParams.AddObjectTypesToQuery(ECC_Pawn);
	ObjectParams.AddObjectTypesToQuery(ECC_WorldDynamic);
	ObjectParams.AddObjectTypesToQuery(ECC_PhysicsBody);

	const int32 Samples = FMath::Max(SamplesPerShape, 1);
	APawn* OwnerPawn = Cast<APawn>(Owner);
	AController* InstigatorController = OwnerPawn ? OwnerPawn->GetController() : nullptr;

	for (int32 i = 0; i < To.Num(); ++i)
	{
		const FMeleeHitShape& Shape = ActiveShapes[FMath::Min(i / Samples, ActiveShapes.Num() - 1)];
		if (!Shape.Component)
		{
			continue;
		}

		TArray<FHitResult> Hits;
		World->SweepMultiByObjectType(Hits, From[i], To[i], FQuat::Identity, ObjectParams, FCollisionShape::MakeSphere(Shape.Radius), Params);

		if (bDebugDraw)
		{
			DrawDebugSphere(World, To[i], Shape.Radius, 8, Hits.Num() > 0 ? FColor::Red : FColor::Green, false, 0.5f);
		}

		for (const FHitResult& Hit : Hits)
		{
			AActor* HitActor = Hit.GetActor();
			if (!HitActor || HitActor == Owner || AlreadyHit.Contains(HitActor))
			{
				continue;
			}

			bool bIgnored = false;
			for (const FName& Tag : IgnoreTags)
			{
				bIgnored |= HitActor->ActorHasTag(Tag);
			}
			if (bIgnored || !HitActor->CanBeDamaged())
			{
				continue;
			}

			AlreadyHit.Add(HitActor);
			UGameplayStatics::ApplyDamage(HitActor, WindowDamage, InstigatorController, Owner, UDamageType::StaticClass());
			OnHit.Broadcast(HitActor, WindowDamage, Hit);
		}
	}
}
