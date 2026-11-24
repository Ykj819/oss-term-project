// Shield enemy: carries a big box shield, its only attack is a short shield rush; stands still for a while after each rush (the opening)

#pragma once

#include "CoreMinimal.h"
#include "EnemyCharacter.h"
#include "EnemyShield.generated.h"

class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class UAnimSequenceBase;

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

	/** The shield: iron tower shield SM_EnemyShield held in both hands (its back grips sit where MM_Shield_* put the hands) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStaticMeshComponent* Shield;

public:

	AEnemyShield();

	virtual void Tick(float DeltaSeconds) override;

	/** Hits from in front of the shield are blocked (no damage) */
	virtual void ResetEnemy() override;

	virtual float TakeDamage(float DamageAmount, struct FDamageEvent const& DamageEvent, class AController* EventInstigator, AActor* DamageCauser) override;

protected:

	/** Blocks attackers within this angle of its facing (each side) */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (ClampMin = 0, ClampMax = 180, Units = "deg"))
	float BlockHalfAngle = 60.f;

	/** Shield flashes this color when it blocks */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield")
	FLinearColor BlockFlashColor = FLinearColor(1.f, 0.85f, 0.4f);

	/** Emissive strength of the block flash */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (ClampMin = 0))
	float BlockFlashGlow = 25.f;

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

	/** Shield size (thickness, width, height); the mesh is 10 x 80 x 110 cm */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (Units = "cm"))
	FVector ShieldSize = FVector(10.f, 80.f, 110.f);

	/** Shield distance in front of the body: hold / pulled in (wind-up) / pushed out (rush). Matches the hands in
	 *  MM_Shield_Hold / Brace / Push (Export/Blender/scripts/mannequin/build_shield_anims.py prints these) */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (Units = "cm"))
	FVector ShieldForward = FVector(38.f, 31.f, 47.f);

	/** Shield centre height above the capsule centre: hold / wind-up / rush (same source as ShieldForward) */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield", meta = (Units = "cm"))
	FVector ShieldLift = FVector(19.f, 23.f, 15.f);

	/** Multiplies the iron colours */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield")
	FLinearColor ShieldColor = FLinearColor(1.f, 1.f, 1.f);

	/** Upper-body poses (both hands on the shield), played on HoldSlotName */
	UPROPERTY(EditAnywhere, Category="Enemy|Shield|Animation")
	TSoftObjectPtr<UAnimSequenceBase> HoldAnim;

	UPROPERTY(EditAnywhere, Category="Enemy|Shield|Animation")
	TSoftObjectPtr<UAnimSequenceBase> BraceAnim;

	UPROPERTY(EditAnywhere, Category="Enemy|Shield|Animation")
	TSoftObjectPtr<UAnimSequenceBase> PushAnim;

	UPROPERTY(EditAnywhere, Category="Enemy|Shield|Animation")
	FName HoldSlotName = TEXT("UpperBody");

	// ---- Runtime ----

	EShieldChargePhase Phase = EShieldChargePhase::None;

	FVector DashDirection = FVector::ForwardVector;
	float SavedMaxAcceleration = 0.f;

	FTimerHandle PhaseTimer;

	void StartWindUp();

	void StartDash();

	void StartRecover();

	void FinishCharge();

	/** Plays one of the shield poses on the upper body (looping) */
	void PlayShieldPose(const TSoftObjectPtr<UAnimSequenceBase>& Anim, float BlendTime);

	/** Puts the movement back to normal chasing */
	void RestoreMovement();
};
