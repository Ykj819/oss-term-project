// Bonfire (rest point): interact (E) to restore health, stamina and potions. Look: SM_Bonfire + SM_BonfireFlame
// (Export/Blender/scripts/props/gen_bonfire.py, Tools/import_bonfire.py)

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interactable.h"
#include "Bonfire.generated.h"

class UStaticMeshComponent;
class UPointLightComponent;

UCLASS()
class ABonfire : public AActor, public IInteractable
{
	GENERATED_BODY()

	/** Stone ring + logs (SM_Bonfire, with collision) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStaticMeshComponent* Body;

	/** Flame (SM_BonfireFlame, M_BonfireFlame: additive, flickers and sways by itself) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStaticMeshComponent* Flame;

	/** Fire glow */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UPointLightComponent* Glow;

public:

	ABonfire();

	// IInteractable
	virtual bool CanInteract_Implementation(AActor* Interactor) const override;
	virtual void Interact_Implementation(AActor* Interactor) override;
	virtual FText GetInteractionPrompt_Implementation() const override;
	virtual void SetInteractionFocus_Implementation(AActor* Interactor, bool bInFocused) override;

	/** Called after the player sat down here (hook for effects / sounds) */
	UFUNCTION(BlueprintImplementableEvent, Category="Bonfire")
	void OnRested(AActor* Interactor);

	/** Where a dead player comes back: RespawnDistance in front of the bonfire (+X), facing it */
	UFUNCTION(BlueprintPure, Category="Bonfire")
	FTransform GetRespawnTransform() const;

	/** The hub bonfire other bonfires can travel to: actor tag "Bonfire_Main" or (editor / PIE) label Bonfire_Main */
	bool IsMainBonfire() const;

	/** First loaded bonfire that IsMainBonfire (null if none / streamed out) */
	static ABonfire* FindMainBonfire(const UWorld* World);

protected:

	virtual void BeginPlay() override;

	virtual void OnConstruction(const FTransform& Transform) override;

	/** Footprint used for the respawn spot (the bonfire mesh is ~150 x 150 cm, flame ~120 cm high) */
	UPROPERTY(EditAnywhere, Category="Bonfire", meta = (Units = "cm"))
	FVector Size = FVector(150.f, 150.f, 80.f);

	/** Flame brightness (material parameter "Glow"); scaled with the light while resting / focused */
	UPROPERTY(EditAnywhere, Category="Bonfire", meta = (ClampMin = 0))
	float FlameGlow = 12.f;

	/** Respawn spot distance from the bonfire, along its forward (red arrow / +X) direction */
	UPROPERTY(EditAnywhere, Category="Bonfire", meta = (ClampMin = 0, Units = "cm"))
	float RespawnDistance = 150.f;

	/** Light color */
	UPROPERTY(EditAnywhere, Category="Bonfire")
	FLinearColor Color = FLinearColor(1.f, 0.35f, 0.02f);

	/** Light brightness normally / while the player is looking at it / right after resting */
	UPROPERTY(EditAnywhere, Category="Bonfire")
	float GlowIntensity = 3000.f;

	UPROPERTY(EditAnywhere, Category="Bonfire")
	float FocusedGlowIntensity = 6000.f;

	UPROPERTY(EditAnywhere, Category="Bonfire")
	float RestFlashIntensity = 20000.f;

	/** How long the rest flash takes to fade */
	UPROPERTY(EditAnywhere, Category="Bonfire", meta = (ClampMin = 0.05, Units = "s"))
	float RestFlashDuration = 0.6f;

	UPROPERTY(Transient)
	TObjectPtr<class UMaterialInstanceDynamic> FlameMaterial;

	/** Light intensity and flame glow together (flame follows the light's ratio to GlowIntensity) */
	void SetFireIntensity(float LightIntensity);

	bool bFocused = false;

	float FlashStartTime = -1.f;

	FTimerHandle FlashTimer;

	void UpdateFlash();

	float GetBaseIntensity() const { return bFocused ? FocusedGlowIntensity : GlowIntensity; }
};
