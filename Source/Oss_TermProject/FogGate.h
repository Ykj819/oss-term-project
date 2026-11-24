// Boss fog gate: a wall of drifting fog the player can walk through in ONE direction only (the blue arrow, +X: from
// behind the gate to the front). From the other side it blocks like a wall. Enemies / bosses are always blocked.
// Optional Boss: when that boss is defeated the fog fades away and the gate stops blocking (both ways).
// Look: 3 engine planes with M_FogGate (Tools/create_fog_gate_material.py), sized by Width / Height.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FogGate.generated.h"

class UBoxComponent;
class UArrowComponent;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;

UCLASS()
class AFogGate : public AActor
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	USceneComponent* Root;

	/** The wall (blocks pawns; the player is let through from the entry side) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UBoxComponent* Blocker;

	/** Direction the player may walk through (editor only) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UArrowComponent* PassDirection;

	UPROPERTY(VisibleAnywhere, Category="Components")
	TArray<TObjectPtr<UStaticMeshComponent>> FogLayers;

public:

	AFogGate();

	virtual void Tick(float DeltaSeconds) override;

	/** Fades the fog out and stops blocking (called automatically when Boss is defeated) */
	UFUNCTION(BlueprintCallable, Category="Fog Gate")
	void Dissolve();

protected:

	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void BeginPlay() override;

	UPROPERTY(EditAnywhere, Category="Fog Gate", meta = (ClampMin = 50, Units = "cm"))
	float Width = 400.f;

	UPROPERTY(EditAnywhere, Category="Fog Gate", meta = (ClampMin = 50, Units = "cm"))
	float Height = 450.f;

	/** Thickness of the blocking wall */
	UPROPERTY(EditAnywhere, Category="Fog Gate", meta = (ClampMin = 2, Units = "cm"))
	float Thickness = 20.f;

	/** Boss behind this gate (pick it in the level with the eyedropper). Empty = the gate stays forever */
	UPROPERTY(EditInstanceOnly, Category="Fog Gate")
	TObjectPtr<AActor> Boss;

	/** Seconds the fog takes to disappear after the boss dies */
	UPROPERTY(EditAnywhere, Category="Fog Gate", meta = (ClampMin = 0.1, Units = "s"))
	float DissolveTime = 2.f;

	UPROPERTY(EditAnywhere, Category="Fog Gate")
	FLinearColor FogColor = FLinearColor(0.85f, 0.88f, 0.95f);

private:

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> FogMaterials;

	/** The player is currently allowed through (entered from the entry side and hasn't left the wall yet) */
	bool bPlayerPassing = false;

	/** A boss was assigned (the reference is cleared once a destroyed boss is garbage collected) */
	bool bHasBoss = false;

	bool bDissolving = false;
	float DissolveAlpha = 0.f;

	bool IsBossDefeated() const;
	void SetPlayerPassing(class ACharacter* Player, bool bPassing);
};
