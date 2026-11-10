// Finds the interactable the owner is facing and uses it on request

#include "InteractionComponent.h"
#include "Interactable.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "CollisionShape.h"

UInteractionComponent::UInteractionComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickInterval = 0.05f;
}

void UInteractionComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	SetFocusedTarget(bInteractionEnabled ? FindBestTarget() : nullptr);

	if (bShowDebugPrompt && FocusedTarget && GEngine)
	{
		const uint64 MessageKey = reinterpret_cast<uint64>(this);
		GEngine->AddOnScreenDebugMessage(MessageKey, 0.1f, FColor::White,
			FString::Printf(TEXT("[%s] %s"), *DebugPromptKey, *GetFocusedPrompt().ToString()), true, FVector2D(1.5f, 1.5f));
	}
}

void UInteractionComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	SetFocusedTarget(nullptr);
	Super::EndPlay(EndPlayReason);
}

bool UInteractionComponent::TryInteract()
{
	AActor* Owner = GetOwner();
	if (!bInteractionEnabled || !IsValid(FocusedTarget) || !IInteractable::Execute_CanInteract(FocusedTarget, Owner))
	{
		return false;
	}

	AActor* Target = FocusedTarget;
	IInteractable::Execute_Interact(Target, Owner);
	OnInteracted.Broadcast(Target);

	// the target may have changed (opened chest -> CanInteract false): refresh right away
	SetFocusedTarget(FindBestTarget());
	return true;
}

FText UInteractionComponent::GetFocusedPrompt() const
{
	return IsValid(FocusedTarget) ? IInteractable::Execute_GetInteractionPrompt(FocusedTarget) : FText::GetEmpty();
}

void UInteractionComponent::SetInteractionEnabled(bool bEnabled)
{
	bInteractionEnabled = bEnabled;
	if (!bEnabled)
	{
		SetFocusedTarget(nullptr);
	}
}

AActor* UInteractionComponent::FindBestTarget() const
{
	AActor* Owner = GetOwner();
	UWorld* World = GetWorld();
	if (!Owner || !World)
	{
		return nullptr;
	}

	const FVector Origin = Owner->GetActorLocation();
	FVector Facing = Owner->GetActorForwardVector();
	Facing.Z = 0.f;
	Facing.Normalize();
	const float MinDot = FMath::Cos(FMath::DegreesToRadians(InteractionMaxAngle));

	FCollisionQueryParams Params(SCENE_QUERY_STAT(InteractionSearch), false, Owner);
	TArray<FOverlapResult> Overlaps;
	World->OverlapMultiByObjectType(Overlaps, Origin, FQuat::Identity, FCollisionObjectQueryParams(FCollisionObjectQueryParams::AllObjects),
		FCollisionShape::MakeSphere(InteractionRange), Params);

	AActor* Best = nullptr;
	float BestScore = TNumericLimits<float>::Max();
	TSet<AActor*> Checked;

	for (const FOverlapResult& Overlap : Overlaps)
	{
		AActor* Candidate = Overlap.GetActor();
		if (!IsValid(Candidate) || Candidate == Owner || Checked.Contains(Candidate))
		{
			continue;
		}
		Checked.Add(Candidate);

		if (!Candidate->Implements<UInteractable>() || !IInteractable::Execute_CanInteract(Candidate, Owner))
		{
			continue;
		}

		// closest point of the candidate's collision (so big doors work when standing at their edge)
		FVector Point = Candidate->GetActorLocation();
		if (UPrimitiveComponent* Prim = Overlap.GetComponent())
		{
			FVector Closest;
			if (Prim->GetClosestPointOnCollision(Origin, Closest) >= 0.f)
			{
				Point = Closest;
			}
		}

		FVector ToPoint = Point - Origin;
		ToPoint.Z = 0.f;
		const float Distance = ToPoint.Size();
		const float Dot = Distance > 1.f ? FVector::DotProduct(Facing, ToPoint / Distance) : 1.f;
		if (Dot < MinDot)
		{
			continue;
		}

		if (bRequireLineOfSight)
		{
			FHitResult Hit;
			if (World->LineTraceSingleByChannel(Hit, Origin, Point, ECC_Visibility, Params) && Hit.GetActor() != Candidate)
			{
				continue;
			}
		}

		// prefer what's in front, then what's close
		const float Score = Distance * (2.f - Dot);
		if (Score < BestScore)
		{
			BestScore = Score;
			Best = Candidate;
		}
	}

	return Best;
}

void UInteractionComponent::SetFocusedTarget(AActor* NewTarget)
{
	if (NewTarget == FocusedTarget)
	{
		return;
	}

	AActor* OldTarget = FocusedTarget;
	FocusedTarget = NewTarget;

	if (IsValid(OldTarget))
	{
		IInteractable::Execute_SetInteractionFocus(OldTarget, GetOwner(), false);
	}
	if (IsValid(NewTarget))
	{
		IInteractable::Execute_SetInteractionFocus(NewTarget, GetOwner(), true);
	}

	OnFocusChanged.Broadcast(NewTarget, OldTarget);
}
