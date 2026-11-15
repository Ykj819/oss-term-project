// Shield enemy: carries a big box shield, its only attack is a short shield rush; stands still for a while after each rush (the opening)

#pragma once

#include "CoreMinimal.h"
#include "EnemyCharacter.h"
#include "EnemyShield.generated.h"

class UStaticMeshComponent;
class UMaterialInstanceDynamic;

UENUM()
enum class EShieldChargePhase : uint8
{
	None,
	WindUp,
	Dash,
	Recover
};

UCLASS()
class AEnemyShield : public AEnemyCharacter
{
	GENERATED_BODY()

	/** The shield: a plain box held in front of the body */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStaticMeshComponent* Shield;

public:

	AEnemyShield();

	virtual void Tick(float DeltaSeconds) override;

	/** Hits from in front of the shield are blocked (no damage) */
	virtual float TakeDamage(float DamageAmount, struct FDamageEvent const& DamageEvent, class AController* EventInstigator, AActor* DamageCauser) override;

protected:

	/** Blocks attackers within this angle of its facing (each side) */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (ClampMin = 0, ClampMax = 180, Units = "deg"))
	float BlockHalfAngle = 60.f;

	/** Shield flashes this color when it blocks */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield")
	FLinearColor BlockFlashColor = FLinearColor(1.f, 0.85f, 0.4f);

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> ShieldMID;

	FTimerHandle BlockFlashTimer;

	virtual void BeginPlay() override;

	virtual void TickCombat(APawn* Player, float Distance, float Now, float DeltaSeconds) override;

	virtual void CancelAttack() override;

	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (ClampMin = 1))
	float MaxHealth = 50.f;

	/** Starts the rush when the player is this close */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (ClampMin = 0, Units = "cm"))
	float ChargeStartRange = 180.f;

	/** Pulls the shield back and aims for this long before rushing (the warning) */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (ClampMin = 0.05, Units = "s"))
	float WindUpTime = 1.f;

	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (ClampMin = 0, Units = "cm/s"))
	float DashSpeed = 300.f;

	/** Rush length in time (distance = DashSpeed * DashTime) */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (ClampMin = 0.05, Units = "s"))
	float DashTime = 0.3f;

	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (ClampMin = 0))
	float ChargeDamage = 25.f;

	/** Stands still this long after the rush */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (ClampMin = 0, Units = "s"))
	float RecoverTime = 2.f;

	/** Shield box size (thickness, width, height) */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (Units = "cm"))
	FVector ShieldSize = FVector(10.f, 80.f, 110.f);

	/** Shield distance in front of the body: normal / pulled back in the wind-up / pushed out in the rush */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (Units = "cm"))
	FVector ShieldForward = FVector(55.f, 35.f, 70.f);

	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (Units = "cm"))
	float ShieldHeight = 5.f;

	UPROPERTY(EditAnywhere, Category="Enemy|Shield")
	FLinearColor ShieldColor = FLinearColor(0.18f, 0.12f, 0.07f);

	// ---- Runtime ----

	EShieldChargePhase Phase = EShieldChargePhase::None;

	FVector DashDirection = FVector::ForwardVector;
	float SavedMaxAcceleration = 0.f;

	FTimerHandle PhaseTimer;

	void StartWindUp();

	void StartDash();

	void StartRecover();

	void FinishCharge();

	/** Puts the movement back to normal chasing */
	void RestoreMovement();
};
