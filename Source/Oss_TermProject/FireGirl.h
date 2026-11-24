// FireGirl: NPC sitting on a stool; talk to her (E) to level up with souls. Doesn't move.
// Look: SM_FireGirl (posed + colour-baked in Blender, Tools/import_firegirl.py) on SM_FireGirl_Stool (same pivot).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interactable.h"
#include "FireGirl.generated.h"

class UCapsuleComponent;
class UStaticMeshComponent;

UCLASS()
class AFireGirl : public AActor, public IInteractable
{
	GENERATED_BODY()

	/** Blocks the player and is what the interaction finds */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UCapsuleComponent* Capsule;

	/** The sitting girl (static pose) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStaticMeshComponent* Body;

	/** The stool she sits on */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStaticMeshComponent* Stool;

public:

	AFireGirl();

	// IInteractable
	virtual bool CanInteract_Implementation(AActor* Interactor) const override;
	virtual void Interact_Implementation(AActor* Interactor) override;
	virtual FText GetInteractionPrompt_Implementation() const override;

	/** All three bosses are dead: she disappears in a puff of smoke (UBossProgressSubsystem calls this) */
	void Vanish();

protected:

	/** Already gone if the bosses were beaten before she streamed in */
	virtual void BeginPlay() override;
};
