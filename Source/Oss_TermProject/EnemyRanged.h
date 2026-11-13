// Ranged enemy: keeps its distance and throws rocks in an arc; backs off when the player closes in, shoves when cornered

#pragma once

#include "CoreMinimal.h"
#include "EnemyCharacter.h"
#include "EnemyRanged.generated.h"

class AEnemyProjectile;
class UStaticMeshComponent;

UCLASS()
class AEnemyRanged : public AEnemyCharacter
{
	GENERATED_BODY()

	/** Rock shown in the right hand during the wind-up */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStaticMeshComponent* HeldRock;

	/** Pouch on the hip (just a look) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStaticMeshComponent* Pouch;

public:

	AEnemyRanged();

protected:

	virtual void BeginPlay() override;

	virtual void TickCombat(APawn* Player, float Distance, float Now, float DeltaSeconds) override;

	virtual void CancelAttack() override;

	/** Lower than the melee enemy: dies quickly once you reach it */
	UPROPERTY(EditAnywhere, Category="Enemy|Ranged", meta = (ClampMin = 1))
	float MaxHealth = 60.f;

	// ---- Distance keeping ----

	/** Throws from up to this distance (needs a clear line of sight) */
	UPROPERTY(EditAnywhere, Category="Enemy|Ranged", meta = (ClampMin = 0, Units = "cm"))
	float ThrowRange = 1800.f;

	/** Starts backing off when the player gets this close */
	UPROPERTY(EditAnywhere, Category="Enemy|Ranged", meta = (ClampMin = 0, Units = "cm"))
	float RetreatRange = 600.f;

	/** Backs off until it is this far away (or the retreat time runs out) */
	UPROPERTY(EditAnywhere, Category="Enemy|Ranged", meta = (ClampMin = 0, Units = "cm"))
	float PreferredRange = 1000.f;

	UPROPERTY(EditAnywhere, Category="Enemy|Ranged", meta = (ClampMin = 0, Units = "cm/s"))
	float RetreatSpeed = 380.f;

	/** Longest it keeps running away in one go */
	UPROPERTY(EditAnywhere, Category="Enemy|Ranged", meta = (ClampMin = 0, Units = "s"))
	float MaxRetreatTime = 1.6f;

	/** Waits this long before it can back off again (stands and fights in between) */
	UPROPERTY(EditAnywhere, Category="Enemy|Ranged", meta = (ClampMin = 0, Units = "s"))
	float RetreatCooldown = 3.5f;

	/** Never backs off further than this from where it was placed */
	UPROPERTY(EditAnywhere, Category="Enemy|Ranged", meta = (ClampMin = 0, Units = "cm"))
	float LeashRadius = 1500.f;

	/** Uses the melee shove (fists) inside this distance */
	UPROPERTY(EditAnywhere, Category="Enemy|Ranged", meta = (ClampMin = 0, Units = "cm"))
	float ShoveRange = 160.f;

	// ---- Throw ----

	UPROPERTY(EditAnywhere, Category="Enemy|Ranged")
	TSoftObjectPtr<UAnimSequenceBase> ThrowAnimation;

	/** Used when ThrowAnimation is missing (not imported yet) */
	UPROPERTY(EditAnywhere, Category="Enemy|Ranged")
	TSoftObjectPtr<UAnimSequenceBase> FallbackThrowAnimation;

	UPROPERTY(EditAnywhere, Category="Enemy|Ranged", meta = (ClampMin = 0.1))
	float ThrowPlayRate = 1.f;

	/** Part of the throw animation (0..1) at which the rock leaves the hand */
	UPROPERTY(EditAnywhere, Category="Enemy|Ranged", meta = (ClampMin = 0, ClampMax = 1))
	float ThrowReleaseFraction = 0.44f;

	UPROPERTY(EditAnywhere, Category="Enemy|Ranged", meta = (ClampMin = 0))
	float ThrowDamage = 15.f;

	/** Rock speed when it leaves the hand */
	UPROPERTY(EditAnywhere, Category="Enemy|Ranged", meta = (ClampMin = 100, Units = "cm/s"))
	float ThrowSpeed = 1700.f;

	/** Rock gravity relative to the world's (lower = flatter arc) */
	UPROPERTY(EditAnywhere, Category="Enemy|Ranged", meta = (ClampMin = 0))
	float RockGravityScale = 0.6f;

	/** How much it leads a moving player (0 = aims where you are, 1 = where you will be). Low = strafing dodges it */
	UPROPERTY(EditAnywhere, Category="Enemy|Ranged", meta = (ClampMin = 0, ClampMax = 1))
	float ThrowLead = 0.35f;

	/** Pause between throws (min, max) */
	UPROPERTY(EditAnywhere, Category="Enemy|Ranged")
	FVector2D ThrowCooldown = FVector2D(1.6f, 3.0f);

	UPROPERTY(EditAnywhere, Category="Enemy|Ranged")
	TSubclassOf<AEnemyProjectile> ProjectileClass;

	// ---- Runtime ----

	bool bThrowing = false;
	bool bRetreating = false;
	float RetreatStartTime = -1000.f;
	float NextRetreatTime = 0.f;
	float ThrowReleaseTime = 0.f;

	FTimerHandle ThrowReleaseTimer;
	FTimerHandle ThrowEndTimer;

	void StartThrow(APawn* Player);

	void ReleaseRock();

	void EndThrow();

	void StopRetreat(float Now);
};
