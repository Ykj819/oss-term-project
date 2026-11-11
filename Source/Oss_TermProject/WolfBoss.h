// Giant wolf boss: circles the player, claws / bites in reach, charges from afar, leaps back when crowded.
// Every animation (including the walk loops) plays as a montage on DefaultSlot of a tiny anim blueprint (ABP_Wolf: Slot -> Output).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "WolfBoss.generated.h"

class UStatsComponent;
class UMeleeHitComponent;
class UBoxComponent;
class UAnimSequenceBase;
class UAnimInstance;
class SWidget;

UENUM(BlueprintType)
enum class EWolfAction : uint8
{
	None,
	ClawRight,
	ClawLeft,
	Bite,
	Charge,
	JumpBack,
	TurnLeft,
	TurnRight
};

UENUM(BlueprintType)
enum class EWolfState : uint8
{
	Dormant,	// waiting for the player
	Recover,	// short pause between actions (punish window)
	Approach,	// walking at the player
	Strafe,		// circling sideways, facing the player
	Action,		// playing an attack / turn / leap (root motion)
	Dead
};

UCLASS()
class AWolfBoss : public ACharacter
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStatsComponent* Stats;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UMeleeHitComponent* MeleeHit;

	/** The capsule only covers the middle of the body: this keeps the player out of the head / hips */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UBoxComponent* BodyBlocker;

public:

	AWolfBoss();

	virtual void Tick(float DeltaSeconds) override;

	virtual float TakeDamage(float DamageAmount, struct FDamageEvent const& DamageEvent, class AController* EventInstigator, AActor* DamageCauser) override;

	/** Back home, full health, waiting again (player died / rested). Does nothing once defeated */
	void ResetBoss();

	UFUNCTION(BlueprintPure, Category="Boss")
	bool IsDefeated() const { return State == EWolfState::Dead; }

protected:

	virtual void BeginPlay() override;

	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	// ---- Setup ----

	/** Anim blueprint with a DefaultSlot (create it once in the editor) */
	UPROPERTY(EditAnywhere, Category="Boss|Setup")
	TSoftClassPtr<UAnimInstance> AnimClass = TSoftClassPtr<UAnimInstance>(FSoftObjectPath(TEXT("/Game/Characters/Wolf/ABP_Wolf.ABP_Wolf_C")));

	UPROPERTY(EditAnywhere, Category="Boss|Setup")
	FName SlotName = TEXT("DefaultSlot");

	/** Name on the health bar */
	UPROPERTY(EditAnywhere, Category="Boss")
	FText BossName = NSLOCTEXT("WolfBoss", "Name", "Great Grey Wolf");

	/** Max health (player stick hits do 15 / 35) */
	UPROPERTY(EditAnywhere, Category="Boss", meta = (ClampMin = 1))
	float BossHealth = 700.f;

	/** Souls for the kill */
	UPROPERTY(EditAnywhere, Category="Boss", meta = (ClampMin = 0))
	int32 SoulReward = 300;

	// ---- Animations ----

	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> WalkForwardAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> WalkLeftAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> WalkRightAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> TurnLeftAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> TurnRightAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> ClawRightAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> ClawLeftAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> BiteAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> ChargeAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> JumpBackAnim;

	// ---- Senses / distances (from the wolf's center) ----

	/** Wakes up when the player comes this close (with line of sight) */
	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "cm")) float AggroRange = 2200.f;

	/** Closer than this: too close for a clean swing -> leap back or snap */
	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "cm")) float TooCloseRange = 320.f;

	/** Claws / bite connect up to here (their root-motion step included) */
	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "cm")) float AttackRange = 480.f;

	/** Charges only from at least this far */
	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "cm")) float MinChargeRange = 750.f;

	/** Turns (45 degree steps) when the player is further off than this to the side */
	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "Degrees")) float TurnAngle = 55.f;

	/** Speeds matching the in-place loops (Wolf_Walk_Fwd = 200, Wolf_Walk_Left/Right = 75) */
	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "cm/s")) float WalkSpeed = 200.f;
	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "cm/s")) float StrafeSpeed = 75.f;

	/** Pause after an action (min, max) — phase 2 uses PhaseTwoRecoverScale of it */
	UPROPERTY(EditAnywhere, Category="Boss|AI") FVector2D RecoverTime = FVector2D(0.7f, 1.3f);

	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "s")) float ChargeCooldown = 8.f;

	/** Chance to leap back when the player is too close, and the minimum time between leaps */
	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (ClampMin = 0, ClampMax = 1)) float JumpBackChance = 0.2f;
	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "s")) float JumpBackCooldown = 8.f;

	// ---- Head look ----

	/** The head (neck) turns toward the player up to this angle on top of the animation */
	UPROPERTY(EditAnywhere, Category="Boss|Look", meta = (Units = "Degrees")) float MaxHeadYaw = 60.f;

	/** How fast the head follows */
	UPROPERTY(EditAnywhere, Category="Boss|Look") float HeadTurnSpeed = 6.f;

	// ---- Phase 2 ----

	/** Below this health fraction the wolf gets faster and chains attacks */
	UPROPERTY(EditAnywhere, Category="Boss|Phase 2", meta = (ClampMin = 0, ClampMax = 1)) float PhaseTwoHealth = 0.5f;
	UPROPERTY(EditAnywhere, Category="Boss|Phase 2", meta = (ClampMin = 0.5)) float PhaseTwoPlayRate = 1.15f;
	UPROPERTY(EditAnywhere, Category="Boss|Phase 2", meta = (ClampMin = 0.1)) float PhaseTwoRecoverScale = 0.55f;

	// ---- Damage ----

	UPROPERTY(EditAnywhere, Category="Boss|Damage") float ClawDamage = 25.f;
	UPROPERTY(EditAnywhere, Category="Boss|Damage") float BiteDamage = 35.f;
	UPROPERTY(EditAnywhere, Category="Boss|Damage") float ChargeDamage = 30.f;

	/** Hit windows as fractions of the animation */
	UPROPERTY(EditAnywhere, Category="Boss|Damage") FVector2D ClawHitWindow = FVector2D(0.27f, 0.43f);
	UPROPERTY(EditAnywhere, Category="Boss|Damage") FVector2D BiteHitWindow = FVector2D(0.29f, 0.41f);
	UPROPERTY(EditAnywhere, Category="Boss|Damage") FVector2D ChargeHitWindow = FVector2D(0.15f, 0.8f);

	/** Draw the attack spheres */
	UPROPERTY(EditAnywhere, Category="Boss|Damage") bool bDebugHits = false;

	// ---- Runtime ----

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Boss")
	EWolfState State = EWolfState::Dormant;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Boss")
	EWolfAction CurrentAction = EWolfAction::None;

	bool bPhaseTwo = false;
	float StateEndTime = 0.f;
	float NextChargeTime = 0.f;
	float NextJumpBackTime = 0.f;
	float HeadYaw = 0.f;

	/** Turns the head toward the player (through UWolfAnimInstance) */
	void UpdateHeadLook(APawn* Player, float DeltaSeconds);
	float StrafeDirection = 1.f;
	EWolfAction LastAttack = EWolfAction::None;
	int32 SameAttackCount = 0;

	/** Follow-up queued by a combo (phase 2) */
	EWolfAction QueuedAction = EWolfAction::None;

	UPROPERTY(Transient) TObjectPtr<UAnimSequenceBase> CurrentLoop;

	FTransform HomeTransform;

	FTimerHandle ActionEndTimer;
	FTimerHandle HitStartTimer;
	FTimerHandle HitEndTimer;
	FTimerHandle CorpseTimer;

	TSharedPtr<SWidget> HealthBar;

	// ---- Helpers ----

	APawn* GetPlayer() const;

	/** Player position in wolf space: distance (2D, centers) and yaw (+ = right) */
	void GetPlayerOffset(const APawn* Player, float& OutDistance, float& OutYaw) const;

	float PlayRate() const { return bPhaseTwo ? PhaseTwoPlayRate : 1.f; }

	/** Plays an animation as a montage on SlotName; returns its real-time length (0 if it couldn't play) */
	float PlayAnim(const TSoftObjectPtr<UAnimSequenceBase>& Anim, float Rate, int32 Loops, float BlendIn, float BlendOut);

	void SetLoop(const TSoftObjectPtr<UAnimSequenceBase>& Anim);
	void StopLoop();

	void Engage();
	void Decide();
	void StartAction(EWolfAction Action);
	void EndAction();
	void EnterRecover();
	void ScheduleHitWindow(EWolfAction Action, float AnimLength);
	void FaceTowards(const FVector& Location, float DeltaSeconds, float DegreesPerSecond);

	/** Picks claw left / right / bite, avoiding a third repeat */
	EWolfAction PickMeleeAttack(float PlayerYaw);

	UFUNCTION()
	void HandleDeath(AActor* DamageCauser);

	void ShowHealthBar(bool bShow);
};
