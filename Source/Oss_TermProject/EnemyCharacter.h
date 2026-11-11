// Basic Soulslike melee enemy: notices the player, walks up, attacks with a readable wind-up, flinches when hit, dies

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "EnemyCharacter.generated.h"

class UStatsComponent;
class UMeleeHitComponent;
class UStaticMeshComponent;
class UAnimSequenceBase;

UENUM(BlueprintType)
enum class EEnemyState : uint8
{
	Idle,
	Chase,
	Attack,
	Stagger,
	Dead
};

UCLASS()
class AEnemyCharacter : public ACharacter
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStatsComponent* Stats;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UMeleeHitComponent* MeleeHit;

	/** Floating health bar (two thin cubes facing the camera; shown once damaged) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStaticMeshComponent* HealthBarBack;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UStaticMeshComponent* HealthBarFill;

public:

	AEnemyCharacter();

	virtual void Tick(float DeltaSeconds) override;

	virtual float TakeDamage(float DamageAmount, struct FDamageEvent const& DamageEvent, class AController* EventInstigator, AActor* DamageCauser) override;

	UFUNCTION(BlueprintPure, Category="Enemy")
	EEnemyState GetState() const { return State; }

	/** Back to its starting spot with full health (revives it if dead) */
	UFUNCTION(BlueprintCallable, Category="Enemy")
	void ResetEnemy();

	/** Resets every enemy in the world (resting at a bonfire, player respawn) */
	static void ResetAllEnemies(const UObject* WorldContext);

protected:

	virtual void BeginPlay() override;

	// ---- Senses / movement ----

	/** Notices the player within this distance (needs a clear line of sight) */
	UPROPERTY(EditAnywhere, Category="Enemy|AI", meta = (ClampMin = 0, Units = "cm"))
	float SightRange = 1500.f;

	/** Gives up the chase beyond this distance */
	UPROPERTY(EditAnywhere, Category="Enemy|AI", meta = (ClampMin = 0, Units = "cm"))
	float LoseSightRange = 2500.f;

	/** Starts an attack within this distance */
	UPROPERTY(EditAnywhere, Category="Enemy|AI", meta = (ClampMin = 0, Units = "cm"))
	float AttackRange = 170.f;

	/** Movement speed while chasing */
	UPROPERTY(EditAnywhere, Category="Enemy|AI", meta = (ClampMin = 0, Units = "cm/s"))
	float ChaseSpeed = 300.f;

	/** Random pause between attacks (min, max) */
	UPROPERTY(EditAnywhere, Category="Enemy|AI")
	FVector2D AttackCooldown = FVector2D(1.2f, 2.4f);

	/** Pause before the first attack after reaching the player */
	UPROPERTY(EditAnywhere, Category="Enemy|AI", meta = (ClampMin = 0, Units = "s"))
	float FirstAttackDelay = 0.5f;

	// ---- Attacks ----

	/** Normal attacks (one picked at random) */
	UPROPERTY(EditAnywhere, Category="Enemy|Attack")
	TArray<TSoftObjectPtr<UAnimSequenceBase>> AttackAnimations;

	/** Heavy attack */
	UPROPERTY(EditAnywhere, Category="Enemy|Attack")
	TSoftObjectPtr<UAnimSequenceBase> HeavyAttackAnimation;

	/** Chance to use the heavy attack */
	UPROPERTY(EditAnywhere, Category="Enemy|Attack", meta = (ClampMin = 0, ClampMax = 1))
	float HeavyAttackChance = 0.25f;

	UPROPERTY(EditAnywhere, Category="Enemy|Attack", meta = (ClampMin = 0))
	float AttackDamage = 20.f;

	UPROPERTY(EditAnywhere, Category="Enemy|Attack", meta = (ClampMin = 0))
	float HeavyAttackDamage = 35.f;

	/** Attack animation speed (below 1 = slower, easier to read wind-up) */
	UPROPERTY(EditAnywhere, Category="Enemy|Attack", meta = (ClampMin = 0.1))
	float AttackPlayRate = 0.85f;

	/** Part of the normal attack animation (0..1) during which the fists can hit */
	UPROPERTY(EditAnywhere, Category="Enemy|Attack")
	FVector2D AttackHitWindow = FVector2D(0.3f, 0.6f);

	/** Part of the heavy attack animation (0..1) during which the fists can hit */
	UPROPERTY(EditAnywhere, Category="Enemy|Attack")
	FVector2D HeavyAttackHitWindow = FVector2D(0.45f, 0.75f);

	/** Keeps turning toward the player during this first part of the attack, then commits to the direction (dodgeable) */
	UPROPERTY(EditAnywhere, Category="Enemy|Attack", meta = (ClampMin = 0, ClampMax = 1))
	float AttackTrackingFraction = 0.3f;

	/** Fist hit sphere radius */
	UPROPERTY(EditAnywhere, Category="Enemy|Attack", meta = (ClampMin = 1, Units = "cm"))
	float FistRadius = 18.f;

	// ---- Getting hit ----

	/** Flinch animation */
	UPROPERTY(EditAnywhere, Category="Enemy|Hit")
	TSoftObjectPtr<UAnimSequenceBase> HitReactAnimation;

	/** How long a hit stops the enemy (interrupts its attack) */
	UPROPERTY(EditAnywhere, Category="Enemy|Hit", meta = (ClampMin = 0, Units = "s"))
	float HitStaggerTime = 0.5f;

	/** The body stays this long after death, then disappears until the next bonfire rest / respawn */
	UPROPERTY(EditAnywhere, Category="Enemy|Hit", meta = (ClampMin = 0, Units = "s"))
	float CorpseLifeSpan = 6.f;

	/** Souls the player gets for killing it */
	UPROPERTY(EditAnywhere, Category="Enemy|Souls", meta = (ClampMin = 0))
	int32 SoulReward = 10;

	/** Health bar size / height above the actor origin */
	UPROPERTY(EditAnywhere, Category="Enemy|Health Bar")
	FVector2D HealthBarSize = FVector2D(90.f, 7.f);

	UPROPERTY(EditAnywhere, Category="Enemy|Health Bar", meta = (Units = "cm"))
	float HealthBarHeight = 120.f;

	// ---- Runtime ----

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Enemy")
	EEnemyState State = EEnemyState::Idle;

	float NextAttackTime = 0.f;
	float AttackStartTime = 0.f;
	float CurrentAttackDuration = 0.f;

	FTimerHandle AttackEndTimer;
	FTimerHandle HitWindowStartTimer;
	FTimerHandle HitWindowEndTimer;
	FTimerHandle StaggerTimer;
	FTimerHandle CorpseTimer;

	/** Starting setup, restored by ResetEnemy */
	FTransform HomeTransform;
	FTransform MeshRelativeTransform;
	FName MeshCollisionProfile;
	ECollisionEnabled::Type CapsuleCollision = ECollisionEnabled::QueryAndPhysics;

	/** AI controller kept across death so it can possess the revived body */
	UPROPERTY(Transient)
	TObjectPtr<AController> SavedController;

	void HideCorpse();

	/** The player, or null if dead / resting at a bonfire / not damageable */
	APawn* GetPlayer() const;

	bool CanSee(const APawn* Player) const;

	void FaceTowards(const FVector& Location, float DeltaSeconds, float Speed);

	void StartAttack();

	void EndAttack();

	void CancelAttack();

	void EndStagger();

	UFUNCTION()
	void HandleDeath(AActor* DamageCauser);

	void UpdateHealthBar();
};
