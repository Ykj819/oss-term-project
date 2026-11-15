// Small wolf enemy (the boss's SK_Wolf scaled down): fast hit-and-run. It runs in to about 5m, crouches (readable wind-up),
// then leaps at the player and bites in mid-air. After landing it pauses (punish window), runs off to get distance and comes again.
// No charge, no standing bite: the jump bite is its only attack.
// Uses /Game/Characters/Wolf/ABP_Wolf (Slot 'DefaultSlot') and Wolf_Run (in-place gallop loop) / Wolf_Jump_Bite (in place; the leap is code).
// Both come from text 'gen_wolf_small.py' in Export/Blender/Wolf_Rig.blend.

#pragma once

#include "CoreMinimal.h"
#include "EnemyCharacter.h"
#include "EnemyWolf.generated.h"

class UAnimInstance;
class UAnimMontage;

UENUM()
enum class EWolfPackPhase : uint8
{
	Approach,	// running in / circling until the leap is ready
	Retreat,	// running away to get leaping distance
	WindUp,		// crouching, aiming
	Leap,		// in the air, jaws open
	Land		// landed: short pause (punish window)
};

UCLASS()
class AEnemyWolf : public AEnemyCharacter
{
	GENERATED_BODY()

public:

	AEnemyWolf();

	virtual void Tick(float DeltaSeconds) override;

	virtual void ResetEnemy() override;

protected:

	virtual void BeginPlay() override;

	virtual void TickCombat(APawn* Player, float Distance, float Now, float DeltaSeconds) override;

	virtual void CancelAttack() override;

	// ---- Setup ----

	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Setup")
	TSoftClassPtr<UAnimInstance> WolfAnimClass = TSoftClassPtr<UAnimInstance>(FSoftObjectPath(TEXT("/Game/Characters/Wolf/ABP_Wolf.ABP_Wolf_C")));

	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Setup")
	TSoftObjectPtr<UAnimSequenceBase> RunAnim;

	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Setup")
	TSoftObjectPtr<UAnimSequenceBase> JumpBiteAnim;

	/** Size compared to the boss (boss = 1, about 3.7m tall) */
	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Setup", meta = (ClampMin = 0.05))
	float MeshScale = 0.35f;

	/** Speed the run animation was made for at MeshScale 1 (Wolf_Run gallop = 857: 6m stride per 0.7s); used to match the legs to the speed */
	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Setup", meta = (Units = "cm/s"))
	float RunAnimSpeedAtFullScale = 857.f;

	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Setup", meta = (ClampMin = 0.1))
	float MaxRunAnimRate = 2.f;

	// ---- Stats ----

	UPROPERTY(EditAnywhere, Category="Enemy|Wolf", meta = (ClampMin = 1))
	float MaxHealth = 80.f;

	/** Running speed (the boss walks at 200 -> x1.5) */
	UPROPERTY(EditAnywhere, Category="Enemy|Wolf", meta = (ClampMin = 0, Units = "cm/s"))
	float RunSpeed = 300.f;

	// ---- Jump bite ----

	/** Leaps from up to this far */
	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Jump Bite", meta = (ClampMin = 0, Units = "cm"))
	float JumpBiteRange = 500.f;

	/** Closer than this it backs off first (too close to leap) */
	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Jump Bite", meta = (ClampMin = 0, Units = "cm"))
	float MinJumpRange = 250.f;

	/** Runs away until it is this far */
	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Jump Bite", meta = (ClampMin = 0, Units = "cm"))
	float RetreatDistance = 450.f;

	/** Crouch before the leap (the player's cue to roll) */
	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Jump Bite", meta = (ClampMin = 0, Units = "s"))
	float WindUpTime = 0.5f;

	/** Time in the air */
	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Jump Bite", meta = (ClampMin = 0.1, Units = "s"))
	float LeapTime = 0.5f;

	/** Lands this far short of the player's center (the jaws reach the rest) */
	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Jump Bite", meta = (ClampMin = 0, Units = "cm"))
	float LandShortOfPlayer = 80.f;

	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Jump Bite", meta = (ClampMin = 0))
	float JumpBiteDamage = 20.f;

	/** Pause after landing (punish window) */
	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Jump Bite", meta = (ClampMin = 0, Units = "s"))
	float LandRecoverTime = 0.8f;

	/** Time between leaps (min, max) */
	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Jump Bite")
	FVector2D JumpCooldown = FVector2D(1.5f, 3.f);

	/** Where in the bite animation the jaws snap shut (0..1); the animation is timed so this happens just before landing.
	 *  Wolf_Jump_Bite (1.8s, made for WindUpTime 0.5 / LeapTime 0.5): snap at frame 57 of 108 -> 0.52 (plays at ~1x) */
	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Jump Bite", meta = (ClampMin = 0, ClampMax = 1))
	float BiteSnapFraction = 0.52f;

	UPROPERTY(EditAnywhere, Category="Enemy|Wolf|Jump Bite")
	bool bDebugBite = false;

	// ---- Runtime ----

	EWolfPackPhase Phase = EWolfPackPhase::Approach;
	float PhaseStartTime = 0.f;
	float NextJumpTime = 0.f;
	float CircleDirection = 1.f;
	float CircleSwitchTime = 0.f;

	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> LoopMontage;

	void SetPhase(EWolfPackPhase NewPhase);

	/** Run loop while moving, speed-matched; stopped when standing */
	void UpdateRunLoop();

	void StartWindUp(APawn* Player);
	void Launch();
	void OpenBiteWindow();
};
