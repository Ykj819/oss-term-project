// Autumn tree boss: a 7m jar-shaped tree that never moves or turns. Branch slams / sweep in front, root spikes that chase
// the player anywhere else; phase 2 roars and starts a leaf storm (falling leaves + blurred, darkened view) and gets faster.
// Every animation plays as a montage on DefaultSlot of a tiny anim blueprint (ABP_Tree: Slot 'DefaultSlot' -> Output Pose).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "TreeBoss.generated.h"

class UStatsComponent;
class UMeleeHitComponent;
class UAnimSequenceBase;
class UAnimInstance;
class UPostProcessComponent;
class UInstancedStaticMeshComponent;
class ARootSpike;
class SWidget;

UENUM(BlueprintType)
enum class ETreeAction : uint8
{
	None,
	SlamRight,
	SlamLeft,
	Sweep,
	Summon,	// arms into the ground, root spikes chase the player
	Roar	// phase 2 start
};

UENUM(BlueprintType)
enum class ETreeState : uint8
{
	Dormant,
	Idle,	// between actions
	Action,
	Dead
};

UCLASS()
class ATreeBoss : public ACharacter
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStatsComponent* Stats;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UMeleeHitComponent* MeleeHit;

	/** Phase 2 view effect (unbound, weight 0 until the storm starts) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UPostProcessComponent* StormPostProcess;

	/** Phase 2 falling leaves (world-space instances around the player) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UInstancedStaticMeshComponent* StormLeaves;

public:

	ATreeBoss();

	virtual void Tick(float DeltaSeconds) override;

	virtual float TakeDamage(float DamageAmount, struct FDamageEvent const& DamageEvent, class AController* EventInstigator, AActor* DamageCauser) override;

	/** Full health, waiting again (player died / rested). Does nothing once defeated */
	void ResetBoss();

	UFUNCTION(BlueprintPure, Category="Boss")
	bool IsDefeated() const { return State == ETreeState::Dead; }

protected:

	virtual void BeginPlay() override;

	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	// ---- Setup ----

	UPROPERTY(EditAnywhere, Category="Boss|Setup")
	TSoftClassPtr<UAnimInstance> AnimClass = TSoftClassPtr<UAnimInstance>(FSoftObjectPath(TEXT("/Game/Characters/Tree/ABP_Tree.ABP_Tree_C")));

	UPROPERTY(EditAnywhere, Category="Boss|Setup")
	FName SlotName = TEXT("DefaultSlot");

	UPROPERTY(EditAnywhere, Category="Boss")
	FText BossName = NSLOCTEXT("TreeBoss", "Name", "Elder of the Crimson Grove");

	UPROPERTY(EditAnywhere, Category="Boss", meta = (ClampMin = 1))
	float BossHealth = 1000.f;

	UPROPERTY(EditAnywhere, Category="Boss", meta = (ClampMin = 0))
	int32 SoulReward = 500;

	// ---- Animations ----

	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> IdleAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> SlamRightAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> SlamLeftAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> SweepAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> SummonAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> RoarAnim;
	UPROPERTY(EditAnywhere, Category="Boss|Animations") TSoftObjectPtr<UAnimSequenceBase> DeathAnim;

	// ---- AI (it never moves or turns: everything is relative to where it was placed) ----

	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "cm")) float AggroRange = 2200.f;

	/** Branch attacks reach this far from the trunk's center */
	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "cm")) float ArmRange = 430.f;

	/** Branch attacks only cover the front: the player must be within this angle of its facing */
	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "Degrees")) float FrontAngle = 100.f;

	/** Pause between actions (min, max) — phase 2 uses PhaseTwoRecoverScale of it */
	UPROPERTY(EditAnywhere, Category="Boss|AI") FVector2D RecoverTime = FVector2D(1.0f, 1.8f);

	/** Minimum time between root summons (from the start of one to the next) */
	UPROPERTY(EditAnywhere, Category="Boss|AI", meta = (Units = "s")) float SummonCooldown = 6.f;

	// ---- Root spikes ----

	/** Spikes per summon (phase 1 / phase 2) */
	UPROPERTY(EditAnywhere, Category="Boss|Roots") FIntPoint SpikeCount = FIntPoint(3, 5);

	/** Time between spikes (phase 1 / phase 2) */
	UPROPERTY(EditAnywhere, Category="Boss|Roots") FVector2D SpikeInterval = FVector2D(0.9f, 0.6f);

	/** First spike when the arms hit the ground (fraction of the summon animation) */
	UPROPERTY(EditAnywhere, Category="Boss|Roots", meta = (ClampMin = 0, ClampMax = 1)) float FirstSpikeFraction = 0.25f;

	UPROPERTY(EditAnywhere, Category="Boss|Roots") float SpikeDamage = 30.f;

	// ---- Phase 2 ----

	UPROPERTY(EditAnywhere, Category="Boss|Phase 2", meta = (ClampMin = 0, ClampMax = 1)) float PhaseTwoHealth = 0.5f;
	UPROPERTY(EditAnywhere, Category="Boss|Phase 2", meta = (ClampMin = 0.5)) float PhaseTwoPlayRate = 1.2f;
	UPROPERTY(EditAnywhere, Category="Boss|Phase 2", meta = (ClampMin = 0.1)) float PhaseTwoRecoverScale = 0.6f;

	/** Leaf storm: number of leaves, and how strong the view effect gets (0..1) */
	UPROPERTY(EditAnywhere, Category="Boss|Phase 2", meta = (ClampMin = 0, ClampMax = 2000)) int32 StormLeafCount = 400;
	UPROPERTY(EditAnywhere, Category="Boss|Phase 2", meta = (ClampMin = 0, ClampMax = 1)) float StormIntensity = 1.f;

	// ---- Damage ----

	UPROPERTY(EditAnywhere, Category="Boss|Damage") float SlamDamage = 40.f;
	UPROPERTY(EditAnywhere, Category="Boss|Damage") float SweepDamage = 30.f;

	/** Hit windows as fractions of the animation (match Tree_*.fbx) */
	UPROPERTY(EditAnywhere, Category="Boss|Damage") FVector2D SlamHitWindow = FVector2D(0.48f, 0.58f);
	UPROPERTY(EditAnywhere, Category="Boss|Damage") FVector2D SweepHitWindow = FVector2D(0.39f, 0.54f);

	UPROPERTY(EditAnywhere, Category="Boss|Damage") bool bDebugHits = false;

	// ---- Runtime ----

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Boss")
	ETreeState State = ETreeState::Dormant;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Boss")
	ETreeAction CurrentAction = ETreeAction::None;

	bool bPhaseTwo = false;
	bool bStorm = false;
	float StormWeight = 0.f;
	float StateEndTime = 0.f;
	float NextSummonTime = 0.f;
	ETreeAction LastAttack = ETreeAction::None;
	int32 SameAttackCount = 0;
	int32 SpikesLeft = 0;

	UPROPERTY(Transient) TObjectPtr<UAnimSequenceBase> CurrentLoop;

	/** Spikes in the world (removed on reset) */
	TArray<TWeakObjectPtr<ARootSpike>> ActiveSpikes;

	/** Leaf storm particles */
	struct FLeaf
	{
		FVector Position;
		FVector Velocity;
		FVector SpinAxis;
		float Spin;
		float SpinSpeed;
	};
	TArray<FLeaf> Leaves;

	FTimerHandle ActionEndTimer;
	FTimerHandle HitStartTimer;
	FTimerHandle HitEndTimer;
	FTimerHandle SpikeTimer;
	FTimerHandle StormStartTimer;

	TSharedPtr<SWidget> HealthBar;

	// ---- Helpers ----

	APawn* GetPlayer() const;
	void GetPlayerOffset(const APawn* Player, float& OutDistance, float& OutYaw) const;
	float PlayRate() const { return bPhaseTwo ? PhaseTwoPlayRate : 1.f; }
	float PlayAnim(const TSoftObjectPtr<UAnimSequenceBase>& Anim, float Rate, int32 Loops, float BlendIn, float BlendOut);
	void PlayIdle();

	void Engage();
	void Decide();
	ETreeAction PickBranchAttack(float PlayerYaw);
	void StartAction(ETreeAction Action);
	void ScheduleHitWindow(ETreeAction Action, float AnimLength);
	void SpawnNextSpike();
	void EndAction();
	void EnterIdle(float Duration);
	void ClearActionTimers();

	void SetStorm(bool bOn);
	void UpdateStorm(float DeltaSeconds);
	void RespawnLeaf(FLeaf& Leaf, const FVector& Center, bool bAnywhere);

	UFUNCTION()
	void HandleDeath(AActor* DamageCauser);

	void ShowHealthBar(bool bShow);
};
