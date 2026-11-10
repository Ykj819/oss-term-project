// Finds the interactable the owner is facing and uses it on request

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "InteractionComponent.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnInteractionFocusChanged, AActor*, NewTarget, AActor*, OldTarget);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnInteracted, AActor*, Target);

UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class UInteractionComponent : public UActorComponent
{
	GENERATED_BODY()

public:

	UInteractionComponent();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Uses the focused interactable; returns true if something was used */
	UFUNCTION(BlueprintCallable, Category="Interaction")
	bool TryInteract();

	/** The interactable that would be used right now (null if none) */
	UFUNCTION(BlueprintPure, Category="Interaction")
	AActor* GetFocusedTarget() const { return FocusedTarget; }

	/** Prompt text of the focused interactable (empty if none) */
	UFUNCTION(BlueprintPure, Category="Interaction")
	FText GetFocusedPrompt() const;

	/** Stops / resumes looking for interactables (e.g. during a cutscene or while dead) */
	UFUNCTION(BlueprintCallable, Category="Interaction")
	void SetInteractionEnabled(bool bEnabled);

	/** Fired when the focused interactable changes (hook the on-screen prompt UI here) */
	UPROPERTY(BlueprintAssignable, Category="Interaction")
	FOnInteractionFocusChanged OnFocusChanged;

	/** Fired after something was interacted with */
	UPROPERTY(BlueprintAssignable, Category="Interaction")
	FOnInteracted OnInteracted;

protected:

	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	/** How far from the owner interactables are found */
	UPROPERTY(EditAnywhere, Category="Interaction", meta = (ClampMin = 0, Units = "cm"))
	float InteractionRange = 200.f;

	/** Only interactables within this angle of the owner's facing are picked */
	UPROPERTY(EditAnywhere, Category="Interaction", meta = (ClampMin = 0, ClampMax = 180, Units = "deg"))
	float InteractionMaxAngle = 80.f;

	/** Require a clear line from the owner to the interactable (no walls in between) */
	UPROPERTY(EditAnywhere, Category="Interaction")
	bool bRequireLineOfSight = true;

	/** Shows "[E] <prompt>" as an on-screen debug message until a real prompt UI exists */
	UPROPERTY(EditAnywhere, Category="Interaction")
	bool bShowDebugPrompt = true;

	/** Key name shown in the debug prompt */
	UPROPERTY(EditAnywhere, Category="Interaction")
	FString DebugPromptKey = TEXT("E");

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Interaction")
	TObjectPtr<AActor> FocusedTarget;

	bool bInteractionEnabled = true;

	/** Best interactable around the owner, or null */
	AActor* FindBestTarget() const;

	void SetFocusedTarget(AActor* NewTarget);
};
