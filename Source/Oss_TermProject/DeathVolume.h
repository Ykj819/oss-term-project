#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DeathVolume.generated.h"

/**
 * Box that kills whatever character touches it (pits, the sea, the arena hole...).
 * Player: health is set to 0 directly, so rolling i-frames / blocking can't save them.
 * Other actors: a huge ApplyDamage.
 * Place it from the Place Actors panel (search "Death Volume") and scale the box in the Details panel.
 */
UCLASS()
class OSS_TERMPROJECT_API ADeathVolume : public AActor
{
	GENERATED_BODY()

public:
	ADeathVolume();

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Death Volume")
	class UBoxComponent* Box;

	/** Also kill enemies / bosses that fall in */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Death Volume")
	bool bKillEnemies = true;

	UFUNCTION()
	void OnBoxOverlap(UPrimitiveComponent* OverlappedComp, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
};
