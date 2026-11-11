// Souls left behind where the player died: walk into it to get them back

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoulDrop.generated.h"

class USphereComponent;
class UStaticMeshComponent;
class UPointLightComponent;

UCLASS()
class ASoulDrop : public AActor
{
	GENERATED_BODY()

	/** Pickup range */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	USphereComponent* PickupSphere;

	/** Glowing orb (temporary look) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStaticMeshComponent* Orb;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UPointLightComponent* Glow;

public:

	ASoulDrop();

	/** Spawns a drop holding Amount souls on the ground below Location */
	static ASoulDrop* SpawnAt(UObject* WorldContext, const FVector& Location, int32 Amount);

	UFUNCTION(BlueprintPure, Category="Souls")
	int32 GetAmount() const { return Amount; }

protected:

	virtual void BeginPlay() override;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Souls")
	int32 Amount = 0;

	/** Orb color */
	UPROPERTY(EditAnywhere, Category="Souls")
	FLinearColor Color = FLinearColor(0.25f, 0.9f, 0.55f);

	UFUNCTION()
	void OnPickupOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	/** Gives the souls to the player if they're alive; returns true if picked up */
	bool TryPickup(AActor* Actor);
};
