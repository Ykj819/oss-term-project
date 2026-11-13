// Withered tree enemy: never moves. A thin white mist always hangs at its roots; when it notices the player
// the mist swells into a wide fog that drains health continuously (blocking / rolling don't help - kill the tree or get out)

#pragma once

#include "CoreMinimal.h"
#include "EnemyCharacter.h"
#include "EnemyFogTree.generated.h"

class UStaticMeshComponent;
class UMaterialInstanceDynamic;

UCLASS()
class AEnemyFogTree : public AEnemyCharacter
{
	GENERATED_BODY()

	/** Trunk, branches and roots hang off this (tips over on death) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	USceneComponent* TreeRoot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	TArray<UStaticMeshComponent*> TreeParts;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	USceneComponent* FogRoot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	TArray<UStaticMeshComponent*> FogPuffs;

public:

	AEnemyFogTree();

	virtual void Tick(float DeltaSeconds) override;

	virtual void ResetEnemy() override;

protected:

	virtual void BeginPlay() override;

	virtual void TickCombat(APawn* Player, float Distance, float Now, float DeltaSeconds) override;

	UPROPERTY(EditAnywhere, Category="Enemy|Fog Tree", meta = (ClampMin = 1))
	float MaxHealth = 120.f;

	/** Fog radius once it has noticed the player */
	UPROPERTY(EditAnywhere, Category="Enemy|Fog Tree", meta = (ClampMin = 0, Units = "cm"))
	float FogRadius = 700.f;

	/** Size of the mist at rest (part of FogRadius) - it already hurts */
	UPROPERTY(EditAnywhere, Category="Enemy|Fog Tree", meta = (ClampMin = 0, ClampMax = 1))
	float IdleFogFraction = 0.25f;

	/** Fog height above the ground */
	UPROPERTY(EditAnywhere, Category="Enemy|Fog Tree", meta = (ClampMin = 0, Units = "cm"))
	float FogHeight = 260.f;

	/** Seconds to spread to full size / to shrink back */
	UPROPERTY(EditAnywhere, Category="Enemy|Fog Tree", meta = (ClampMin = 0.1, Units = "s"))
	float FogSpreadTime = 2.f;

	UPROPERTY(EditAnywhere, Category="Enemy|Fog Tree", meta = (ClampMin = 0))
	float FogDamagePerSecond = 8.f;

	/** Damage is dealt in steps this far apart */
	UPROPERTY(EditAnywhere, Category="Enemy|Fog Tree", meta = (ClampMin = 0.05, Units = "s"))
	float FogDamageInterval = 0.5f;

	UPROPERTY(EditAnywhere, Category="Enemy|Fog Tree")
	FLinearColor FogColor = FLinearColor(0.92f, 0.93f, 0.95f, 0.16f);

	UPROPERTY(EditAnywhere, Category="Enemy|Fog Tree")
	FLinearColor BarkColor = FLinearColor(0.11f, 0.095f, 0.08f);

	// ---- Runtime ----

	/** 0 = gone, IdleFogFraction = resting mist, 1 = full fog */
	float FogAmount = 0.f;
	float FogDamageTimer = 0.f;
	float DeathTime = -1.f;
	FVector FallAxis = FVector::ForwardVector;

	struct FPuff
	{
		float Angle;
		float RadiusFrac;
		float Height;
		float Size;
		float Drift;
		float Phase;
	};
	TArray<FPuff> Puffs;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> FogMaterial;

	void UpdateFog(float DeltaSeconds, float Now);

	void DamagePlayerInFog(float DeltaSeconds);

	float GroundZ() const;
};
