// Temporary enemy stand-in: a sphere the player can lock on to

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LockOnDummy.generated.h"

class UStaticMeshComponent;

UCLASS()
class ALockOnDummy : public AActor
{
	GENERATED_BODY()

	/** Sphere body */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStaticMeshComponent* Body;

public:

	ALockOnDummy();

protected:

	virtual void BeginPlay() override;

	/** Sphere diameter */
	UPROPERTY(EditAnywhere, Category="Dummy", meta = (ClampMin = 10, Units = "cm"))
	float Diameter = 150.f;

	/** Sphere color */
	UPROPERTY(EditAnywhere, Category="Dummy")
	FLinearColor Color = FLinearColor(0.6f, 0.05f, 0.05f);

	/** Test attack: when the player is close, glow, then hit them (for testing dodge / block timing) */
	UPROPERTY(EditAnywhere, Category="Dummy|Test Attack")
	bool bAttackPlayer = true;

	/** Time between attacks */
	UPROPERTY(EditAnywhere, Category="Dummy|Test Attack", meta = (ClampMin = 0.5, Units = "s"))
	float AttackInterval = 2.5f;

	/** How long the sphere glows before the hit lands (the hit happens the moment the glow ends) */
	UPROPERTY(EditAnywhere, Category="Dummy|Test Attack", meta = (ClampMin = 0.05, Units = "s"))
	float AttackWindup = 0.7f;

	/** Damage per hit */
	UPROPERTY(EditAnywhere, Category="Dummy|Test Attack", meta = (ClampMin = 0))
	float AttackDamage = 20.f;

	/** The player must be this close (from the sphere's surface) to be attacked */
	UPROPERTY(EditAnywhere, Category="Dummy|Test Attack", meta = (ClampMin = 0, Units = "cm"))
	float AttackRange = 250.f;

	/** Glow color during the wind-up */
	UPROPERTY(EditAnywhere, Category="Dummy|Test Attack")
	FLinearColor WindupColor = FLinearColor(1.f, 0.8f, 0.f);

	UPROPERTY(Transient)
	TObjectPtr<class UMaterialInstanceDynamic> BodyMaterial;

	FTimerHandle AttackLoopTimer;
	FTimerHandle AttackHitTimer;

	/** Player within reach? */
	APawn* GetPlayerInRange() const;

	void StartAttack();

	void LandAttack();

	virtual void OnConstruction(const FTransform& Transform) override;
};
