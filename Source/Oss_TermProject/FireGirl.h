// FireGirl: standing NPC; talk to her (E) to level up with souls. Doesn't move.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interactable.h"
#include "FireGirl.generated.h"

class UCapsuleComponent;
class USkeletalMeshComponent;
class UAnimSequenceBase;

UCLASS()
class AFireGirl : public AActor, public IInteractable
{
	GENERATED_BODY()

	/** Blocks the player and is what the interaction finds */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UCapsuleComponent* Capsule;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	USkeletalMeshComponent* Mesh;

public:

	AFireGirl();

	// IInteractable
	virtual bool CanInteract_Implementation(AActor* Interactor) const override;
	virtual void Interact_Implementation(AActor* Interactor) override;
	virtual FText GetInteractionPrompt_Implementation() const override;

protected:

	virtual void BeginPlay() override;

	/** Looping idle animation */
	UPROPERTY(EditAnywhere, Category="FireGirl")
	TSoftObjectPtr<UAnimSequenceBase> IdleAnimation;
};
