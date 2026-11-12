// Fishman boss: a 2x scaled mannequin brawler. Two-handed overhead slam, jump with a landing shockwave around it,
// right / left foot stomps. Walks with ABP_Unarmed (played at half rate so the giant's strides match its speed);
// attacks play as montages on DefaultSlot. Swap the mesh in a Blueprint child for the final model (same mannequin skeleton).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "FishmanBoss.generated.h"

class UStatsComponent;
class UMeleeHitComponent;
class UAnimSequenceBase;
class SWidget;

UENUM(BlueprintType)
enum class EFishmanAction : uint8
{
	None,
	Slam,		// both fists overhead, then down onto the ground in front
	JumpSlam,	// jumps in place, shockwave all around on landing
	StompRight,
	StompLeft
};

UENUM(BlueprintType)
enum class EFishmanState : uint8
{
	Dormant,	// waiting for the player
	Recover,	// pause between actions (punish window), turns toward the player
	Approach,	// walking at the player
	Action,		// attacking
	Dead
};

UCLASS()
class AFishmanBoss : public ACharacter
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStatsComponent* Stats;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UMeleeHitComponent* MeleeHit;

public:

	AFishmanBoss();

	virtual void Tick(float DeltaSeconds) override;

	virtual float TakeDamage(float DamageAmount, struct FDamageEvent const& DamageEvent, class AController* EventInstigator, AActor* DamageCauser) override;

	/** Back home, full health, waiting again (player died / rested). Does nothing once defeated */
	void ResetBoss();

	UFUNCTION(BlueprintPure, Category="Boss")
	bool IsDefeated() const { return State == EFishmanState::Dead; }

protected:

	virtual void BeginPlay() override;

	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	// ---- Setup ----

	/** Body size relative to the player (capsule, mesh; attack reach scales with it) */
	UPROPERTY(EditDefaultsOnly, Category="Boss|Setup", meta = (ClampMin = 0.5))
	float BossScale = 2.f;

	UPROPERTY(EditAnywhere, Category="Boss|Setup")
	FName SlotName = TEXT("DefaultSlot");

	UPROPERTY(EditAnywhere, Category="Boss")
	FText BossName = NSLOCTEXT("FishmanBoss", "Name", "Fishman");

	/** Max health (player stick hits do 15 / 35) */
	UPROPERTY(EditAnywhere, Category="Boss", meta = (ClampMin = 1))
	float BossHealth = 800.f;

	UPROPERTY(EditAnywhere, Category="Boss", meta = (ClampMin = 0))
	int32 SoulReward = 350;

	// ---- Animations ----

	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> SlamAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> JumpSlamAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> StompRightAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> StompLeftAnim;

	// ---- AI (distances from the boss's center, already at boss size) ----

	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "cm")) float AggroRange = 2000.f;

	/** Slam / stomps start within this distance */
	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "cm")) float AttackRange = 300.f;

	/** Player this close and beside / behind it -> jump slam (punishes circling) */
	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "cm")) float CrowdedRange = 380.f;

	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "cm/s")) float WalkSpeed = 260.f;

	/** Turning speed between attacks */
	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "Degrees")) float TurnRate = 100.f;

	/** Pause after an attack (min, max) — phase 2 uses PhaseTwoRecoverScale of it */
	UPROPERTY(EditAnywhere, Category="Boss|AI") FVector2D RecoverTime = FVector2D(0.9f, 1.6f);

	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (ClampMin = 0, ClampMax = 1)) float JumpSlamChance = 0.15f;

	// ---- Phase 2 ----

	UPROPERTY(EditAnywhere, Category="Boss|Phase 2", meta = (ClampMin = 0, ClampMax = 1)) float PhaseTwoHealth = 0.5f;
	UPROPERTY(EditAnywhere, Category="Boss|Phase 2", meta = (ClampMin = 0.5)) float PhaseTwoPlayRate = 1.15f;
	UPROPERTY(EditAnywhere, Category="Boss|Phase 2", meta = (ClampMin = 0.1)) float PhaseTwoRecoverScale = 0.6f;

	// ---- Damage ----

	UPROPERTY(EditAnywhere, Category="Boss|Damage") float SlamDamage = 40.f;
	UPROPERTY(EditAnywhere, Category="Boss|Damage") float JumpSlamDamage = 35.f;
	UPROPERTY(EditAnywhere, Category="Boss|Damage") float StompDamage = 28.f;

	/** Shockwave radius around the boss when it lands */
	UPROPERTY(EditAnywhere, Category="Boss|Damage", meta = (Units = "cm")) float JumpSlamRadius = 420.f;

	/** Hit windows as fractions of the animation (match the impact frames of Fish_*.fbx) */
	UPROPERTY(EditAnywhere, Category="Boss|Damage") FVector2D SlamHitWindow = FVector2D(0.45f, 0.55f);
	UPROPERTY(EditAnywhere, Category="Boss|Damage") FVector2D JumpSlamHitWindow = FVector2D(0.5f, 0.56f);
	UPROPERTY(EditAnywhere, Category="Boss|Damage") FVector2D StompHitWindow = FVector2D(0.42f, 0.52f);

	/** Keeps turning toward the player during this first part of the slam / stomps, then commits (dodgeable) */
	UPROPERTY(EditAnywhere, Category="Boss|Damage", meta = (ClampMin = 0, ClampMax = 1)) float AttackTrackingFraction = 0.35f;

	/** Draw the attack spheres */
	UPROPERTY(EditAnywhere, Category="Boss|Damage") bool bDebugHits = false;

	// ---- Runtime ----

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Boss")
	EFishmanState State = EFishmanState::Dormant;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Boss")
	EFishmanAction CurrentAction = EFishmanAction::None;

	bool bPhaseTwo = false;
	float StateEndTime = 0.f;
	EFishmanAction LastAttack = EFishmanAction::None;
	int32 SameAttackCount = 0;
	EFishmanAction QueuedAction = EFishmanAction::None;

	FTransform HomeTransform;

	FTimerHandle ActionEndTimer;
	FTimerHandle HitStartTimer;
	FTimerHandle HitEndTimer;
	FTimerHandle CorpseTimer;

	TSharedPtr<SWidget> HealthBar;

	// ---- Helpers ----

	APawn* GetPlayer() const;

	/** Player position in boss space: distance (2D) and yaw (+ = right) */
	void GetPlayerOffset(const APawn* Player, float& OutDistance, float& OutYaw) const;

	float PlayRate() const { return bPhaseTwo ? PhaseTwoPlayRate : 1.f; }

	/** Locomotion (ABP_Unarmed) runs at 1/BossScale so the big strides match the walk speed; attacks at normal rate */
	void SetLocomotionRate(bool bLocomotion);

	void FaceTowards(const FVector& Location, float DeltaSeconds, float DegreesPerSecond);

	void Engage();
	void Decide();
	EFishmanAction PickAttack(float Distance, float PlayerYaw);
	void StartAction(EFishmanAction Action);
	void ScheduleHitWindow(EFishmanAction Action, float AnimLength);
	void EndAction();
	void EnterRecover();

	UFUNCTION()
	void HandleDeath(AActor* DamageCauser);

	void ShowHealthBar(bool bShow);
};
