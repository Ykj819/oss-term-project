// Root spike for the tree boss: a glowing warning circle on the ground, then wooden spikes burst up and hurt the player
// standing in it, then sink back. Built from engine basic shapes (no assets needed).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RootSpike.generated.h"

class UStaticMeshComponent;
class UMaterialInstanceDynamic;

UCLASS()
class ARootSpike : public AActor
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, Category="Components")
	TObjectPtr<UStaticMeshComponent> Warning;

	UPROPERTY(VisibleAnywhere, Category="Components")
	TArray<TObjectPtr<UStaticMeshComponent>> Spikes;

public:

	ARootSpike();

	virtual void Tick(float DeltaSeconds) override;

	/** Damage radius (also the warning circle size) */
	UPROPERTY(EditAnywhere, Category="Root Spike", meta = (Units = "cm")) float Radius = 140.f;

	/** Time between the warning appearing and the spikes bursting up */
	UPROPERTY(EditAnywhere, Category="Root Spike", meta = (Units = "s")) float WarnTime = 1.1f;

	UPROPERTY(EditAnywhere, Category="Root Spike", meta = (Units = "cm")) float Height = 300.f;

	UPROPERTY(EditAnywhere, Category="Root Spike") float Damage = 30.f;

protected:

	virtual void BeginPlay() override;

	float Age = 0.f;
	bool bHasHit = false;

	/** Final relative transforms of the spikes (scaled from 0 height while rising) */
	TArray<FTransform> SpikeTargets;

	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> WarningMaterial;

	void TryHitPlayer();
};
