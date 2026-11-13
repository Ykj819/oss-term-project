// Spiked ball enemy: only charges. Revs up in place (warning), rolls straight at where the player was,
// then sits dazed for a few seconds before it can move again (the window to punish it)

#pragma once

#include "CoreMinimal.h"
#include "EnemyCharacter.h"
#include "EnemyBall.generated.h"

class UStaticMeshComponent;
class UMaterialInstanceDynamic;

UCLASS()
class AEnemyBall : public AEnemyCharacter
{
	GENERATED_BODY()

	/** Rolls the ball and its spikes (absolute rotation, so it never turns with the capsule) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	USceneComponent* BallPivot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStaticMeshComponent* Ball;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	TArray<UStaticMeshComponent*> Spikes;

public:

	AEnemyBall();

	virtual void Tick(float DeltaSeconds) override;

	virtual void ResetEnemy() override;

protected:

	virtual void BeginPlay() override;

	virtual void TickCombat(APawn* Player, float Distance, float Now, float DeltaSeconds) override;

	virtual void CancelAttack() override;

	UPROPERTY(EditAnywhere, Category="Enemy|Ball", meta = (ClampMin = 10, Units = "cm"))
	float BallRadius = 55.f;

	UPROPERTY(EditAnywhere, Category="Enemy|Ball", meta = (ClampMin = 1))
	float MaxHealth = 80.f;

	/** Damage of a charge that connects */
	UPROPERTY(EditAnywhere, Category="Enemy|Ball", meta = (ClampMin = 0))
	float ChargeDamage = 50.f;

	/** Charges when the player is within this distance (and visible) */
	UPROPERTY(EditAnywhere, Category="Enemy|Ball", meta = (ClampMin = 0, Units = "cm"))
	float ChargeRange = 1600.f;

	/** Revving up in place before the charge (aims during this, then the direction is locked) */
	UPROPERTY(EditAnywhere, Category="Enemy|Ball", meta = (ClampMin = 0, Units = "s"))
	float WindUpTime = 0.9f;

	UPROPERTY(EditAnywhere, Category="Enemy|Ball", meta = (ClampMin = 0, Units = "cm/s"))
	float ChargeSpeed = 1500.f;

	/** Keeps rolling this far past where the player stood */
	UPROPERTY(EditAnywhere, Category="Enemy|Ball", meta = (ClampMin = 0, Units = "cm"))
	float ChargeOvershoot = 400.f;

	UPROPERTY(EditAnywhere, Category="Enemy|Ball", meta = (ClampMin = 0, Units = "cm"))
	float MaxChargeDistance = 2400.f;

	/** After a charge it can't move for this long */
	UPROPERTY(EditAnywhere, Category="Enemy|Ball", meta = (ClampMin = 0, Units = "s"))
	float RestTime = 5.f;

	/** Push given to the player on a hit */
	UPROPERTY(EditAnywhere, Category="Enemy|Ball", meta = (ClampMin = 0, Units = "cm/s"))
	float KnockbackSpeed = 700.f;

	UPROPERTY(EditAnywhere, Category="Enemy|Ball")
	FLinearColor BallColor = FLinearColor(0.05f, 0.06f, 0.08f);

	/** Color it glows toward while revving up */
	UPROPERTY(EditAnywhere, Category="Enemy|Ball")
	FLinearColor WarningColor = FLinearColor(0.9f, 0.12f, 0.02f);

	// ---- Runtime ----

	enum class EBallPhase : uint8 { Ready, WindUp, Charging, Resting };
	EBallPhase Phase = EBallPhase::Ready;

	float PhaseStartTime = 0.f;
	FVector ChargeDir = FVector::ForwardVector;
	FVector ChargeStart = FVector::ZeroVector;
	float ChargeDistance = 0.f;
	bool bChargeResolved = false;		// hit / blocked / dodged: the player is no longer checked this charge
	float DeathTime = -1.f;
	float DefaultMaxAcceleration = 2048.f;
	float DefaultBraking = 2048.f;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> BallMaterials;

	void StartWindUp(float Now);

	void StartCharge(APawn* Player, float Now);

	/** bBounce = hit something: hop back a little */
	void EndCharge(float Now, bool bBounce);

	void TryHitPlayer(APawn* Player);

	void RollBall(const FVector& Velocity, float DeltaSeconds);

	void SetGlow(float Alpha);

	void SetPassThroughPawns(bool bPass);
};
