// Small leech enemy: lies still on the ground. When the player comes close it rears up (readable wind-up) and leaps onto
// the player's body, then drains health every second (blocking doesn't help, a roll at the right moment dodges the leap).
// It can't be hit: pressing E (interact) ShakeOffPresses times pulls it off, and it dies when it hits the ground.

#pragma once

#include "CoreMinimal.h"
#include "EnemyCharacter.h"
#include "EnemyLeech.generated.h"

class UStaticMeshComponent;
class UCapsuleComponent;
class UMaterialInstanceDynamic;

UENUM()
enum class ELeechPhase : uint8
{
	Resting,	// on the ground, waiting
	WindUp,		// rearing up before the leap
	Leaping,	// flying at the player
	Attached,	// stuck to the player, draining health
	Recovering	// shaken off / missed: lying on the ground, can't leap
};

UCLASS()
class AEnemyLeech : public AEnemyCharacter
{
	GENERATED_BODY()

	/** Body segments hang off this (origin = belly / ground under the capsule) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	USceneComponent* BodyRoot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	TArray<UStaticMeshComponent*> Segments;

	/** Red sucker mouth at the front */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStaticMeshComponent* Mouth;

public:

	AEnemyLeech();

	virtual void Tick(float DeltaSeconds) override;

	virtual void ResetEnemy() override;

	/** Called by the player's E (interact) press: counts toward pulling off the oldest leech stuck to Player. False if none is attached */
	static bool TryShakeOff(APawn* Player);

	bool IsAttachedToPlayer(const APawn* Player) const { return Phase == ELeechPhase::Attached && AttachedPlayer.Get() == Player; }

protected:

	virtual void BeginPlay() override;

	virtual void TickCombat(APawn* Player, float Distance, float Now, float DeltaSeconds) override;

	UPROPERTY(EditAnywhere, Category="Enemy|Leech", meta = (ClampMin = 1))
	float MaxHealth = 30.f;

	/** Leaps when the player gets this close */
	UPROPERTY(EditAnywhere, Category="Enemy|Leech", meta = (ClampMin = 0, Units = "cm"))
	float LatchRange = 230.f;

	/** Rearing up before the leap (the player's chance to roll) */
	UPROPERTY(EditAnywhere, Category="Enemy|Leech", meta = (ClampMin = 0, Units = "s"))
	float WindUpTime = 0.4f;

	/** Flight time of the leap (the leech homes in on the player) */
	UPROPERTY(EditAnywhere, Category="Enemy|Leech", meta = (ClampMin = 0.05, Units = "s"))
	float LeapDuration = 0.35f;

	UPROPERTY(EditAnywhere, Category="Enemy|Leech", meta = (ClampMin = 0, Units = "cm"))
	float LeapArcHeight = 60.f;

	/** Health drained per second while attached (straight to health: no block, no flinch) */
	UPROPERTY(EditAnywhere, Category="Enemy|Leech", meta = (ClampMin = 0))
	float DrainPerSecond = 5.f;

	/** Drain is dealt in steps this far apart */
	UPROPERTY(EditAnywhere, Category="Enemy|Leech", meta = (ClampMin = 0.05, Units = "s"))
	float DrainInterval = 0.2f;

	/** E presses needed to pull it off */
	UPROPERTY(EditAnywhere, Category="Enemy|Leech", meta = (ClampMin = 1))
	int32 ShakeOffPresses = 3;

	/** Pulled off: dies when it lands (or after this long at most) */
	UPROPERTY(EditAnywhere, Category="Enemy|Leech", meta = (ClampMin = 0, Units = "s"))
	float ShakenOffMaxFallTime = 1.5f;

	/** Recovery after a missed leap */
	UPROPERTY(EditAnywhere, Category="Enemy|Leech", meta = (ClampMin = 0, Units = "s"))
	float MissRecoverTime = 1.2f;

	/** Extra wait after recovering before it can leap again */
	UPROPERTY(EditAnywhere, Category="Enemy|Leech", meta = (ClampMin = 0, Units = "s"))
	float RelatchCooldown = 1.5f;

	/** How hard it's flung when pulled off */
	UPROPERTY(EditAnywhere, Category="Enemy|Leech", meta = (ClampMin = 0, Units = "cm/s"))
	float ShakeOffThrowSpeed = 380.f;

	/** Places on the player's body it can stick to (relative to the player's capsule center: X forward, Y right, Z up). It picks the one facing it */
	UPROPERTY(EditAnywhere, Category="Enemy|Leech")
	TArray<FVector> AttachSpots;

	UPROPERTY(EditAnywhere, Category="Enemy|Leech")
	FLinearColor BodyColor = FLinearColor(0.012f, 0.018f, 0.04f);	// blue-black

	UPROPERTY(EditAnywhere, Category="Enemy|Leech")
	FLinearColor MouthColor = FLinearColor(0.35f, 0.02f, 0.02f);

	/** On-screen "press E" hint while attached */
	UPROPERTY(EditAnywhere, Category="Enemy|Leech")
	bool bShowShakeOffHint = true;

	// ---- Runtime ----

	ELeechPhase Phase = ELeechPhase::Resting;
	float PhaseStartTime = 0.f;
	float NextLatchTime = 0.f;

	TWeakObjectPtr<APawn> AttachedPlayer;
	int32 AttachSpotIndex = 0;
	float AttachRoll = 0.f;
	int32 ShakeCount = 0;
	float LastShakeTime = -1000.f;
	float DrainTimer = 0.f;
	/** Health drunk so far this time (it swells up) */
	float DrunkAmount = 0.f;

	FVector LeapStart = FVector::ZeroVector;
	FQuat LeapStartQuat = FQuat::Identity;
	FVector LeapDir = FVector::ForwardVector;

	/** How long the current Recovering phase lasts */
	float RecoverDuration = 0.f;

	/** Pulled off the player: dies on landing */
	bool bShakenOff = false;

	float DeathTime = -1.f;

	/** Segment rest layout (relative to BodyRoot) */
	TArray<FVector> SegmentBaseLocations;
	TArray<FVector> SegmentBaseScales;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> SegmentMaterials;

	void SetPhase(ELeechPhase NewPhase);

	void StartWindUp(APawn* Player);
	void StartLeap();
	void UpdateLeap(float Now);
	void Attach(APawn* Player);
	void UpdateAttached(float DeltaSeconds, float Now);

	/** One E press */
	void RegisterShakePress();

	/** Off the player and onto the ground: bThrown = pulled off (flung, long stun), otherwise a missed leap / player gone */
	void Detach(bool bThrown);

	/** Picks the body spot that faces the leech */
	int32 PickAttachSpot(const APawn* Player) const;

	/** Where the leech's origin and rotation go for a spot, relative to the player's capsule */
	FTransform GetSpotTransform(int32 SpotIndex) const;

	/** Physics / collision for being on the ground (true) or stuck to / flying at the player (false) */
	void SetGroundMode(bool bOnGround);

	void UpdateBody(float DeltaSeconds, float Now);

	void ShowHint() const;
};
