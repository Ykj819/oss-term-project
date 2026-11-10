// Anything the player can interact with (E): chests, doors, levers, NPCs, items on the ground...

#pragma once

#include "CoreMinimal.h"
#include "UObject/Interface.h"
#include "Interactable.generated.h"

UINTERFACE(MinimalAPI, Blueprintable)
class UInteractable : public UInterface
{
	GENERATED_BODY()
};

/**
 *  Implement on an actor (in C++ or in a Blueprint: Class Settings -> Interfaces -> Add -> Interactable)
 *  to make the player's InteractionComponent pick it up.
 *  The actor needs a component with collision (Query enabled) so it can be found.
 */
class IInteractable
{
	GENERATED_BODY()

public:

	/** Can Interactor use this right now? (e.g. false for an already opened chest or a locked door) */
	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category="Interaction")
	bool CanInteract(AActor* Interactor) const;
	virtual bool CanInteract_Implementation(AActor* Interactor) const { return true; }

	/** Called when Interactor presses the interact key while this is focused */
	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category="Interaction")
	void Interact(AActor* Interactor);
	virtual void Interact_Implementation(AActor* Interactor) {}

	/** Short verb shown in the prompt, e.g. "Open", "Talk", "Pick up" */
	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category="Interaction")
	FText GetInteractionPrompt() const;
	virtual FText GetInteractionPrompt_Implementation() const { return NSLOCTEXT("Interaction", "DefaultPrompt", "Interact"); }

	/** Called when this becomes / stops being the player's current interaction target (use it for a highlight or a sound) */
	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category="Interaction")
	void SetInteractionFocus(AActor* Interactor, bool bFocused);
	virtual void SetInteractionFocus_Implementation(AActor* Interactor, bool bFocused) {}
};
