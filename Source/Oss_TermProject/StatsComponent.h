// Health and stamina for the player (and later enemies)

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "StatsComponent.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnStatChanged, float, NewValue, float, MaxValue);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnDeath, AActor*, DamageCauser);

UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class UStatsComponent : public UActorComponent
{
	GENERATED_BODY()

public:

	UStatsComponent();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	// ---- Health ----

	/** Lowers health; returns the damage actually taken. Reaching 0 fires OnDeath once */
	UFUNCTION(BlueprintCallable, Category="Stats|Health")
	float ApplyDamage(float Amount, AActor* DamageCauser = nullptr);

	/** Restores health (not above max, not when dead) */
	UFUNCTION(BlueprintCallable, Category="Stats|Health")
	void Heal(float Amount);

	/** Back to full health and stamina (e.g. resting at a checkpoint / respawning) */
	UFUNCTION(BlueprintCallable, Category="Stats")
	void RestoreAll();

	UFUNCTION(BlueprintPure, Category="Stats|Health")
	float GetHealth() const { return Health; }

	UFUNCTION(BlueprintPure, Category="Stats|Health")
	float GetMaxHealth() const { return MaxHealth; }

	/** Changes max health (leveling up); current health moves by the same amount */
	UFUNCTION(BlueprintCallable, Category="Stats|Health")
	void SetMaxHealth(float NewMax);

	/** Changes max stamina (leveling up); current stamina moves by the same amount */
	UFUNCTION(BlueprintCallable, Category="Stats|Stamina")
	void SetMaxStamina(float NewMax);

	UFUNCTION(BlueprintPure, Category="Stats|Health")
	bool IsDead() const { return bIsDead; }

	// ---- Stamina ----

	/** Soulslike rule: an action can start as long as there is any stamina left (it may cost more than what's left) */
	UFUNCTION(BlueprintPure, Category="Stats|Stamina")
	bool HasStamina() const { return Stamina > 0.f; }

	/** Spends stamina (clamped at 0) and pauses regeneration for a moment. Returns false (and spends nothing) if out of stamina */
	UFUNCTION(BlueprintCallable, Category="Stats|Stamina")
	bool ConsumeStamina(float Amount);

	/** Spends stamina continuously (call every frame, e.g. while sprinting). Regeneration stays paused while draining */
	UFUNCTION(BlueprintCallable, Category="Stats|Stamina")
	void DrainStamina(float AmountPerSecond, float DeltaTime);

	UFUNCTION(BlueprintPure, Category="Stats|Stamina")
	float GetStamina() const { return Stamina; }

	UFUNCTION(BlueprintPure, Category="Stats|Stamina")
	float GetMaxStamina() const { return MaxStamina; }

	// ---- Events ----

	UPROPERTY(BlueprintAssignable, Category="Stats")
	FOnStatChanged OnHealthChanged;

	UPROPERTY(BlueprintAssignable, Category="Stats")
	FOnStatChanged OnStaminaChanged;

	UPROPERTY(BlueprintAssignable, Category="Stats")
	FOnDeath OnDeath;

protected:

	virtual void BeginPlay() override;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Stats|Health", meta = (ClampMin = 1))
	float MaxHealth = 100.f;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Stats|Health")
	float Health = 100.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Stats|Stamina", meta = (ClampMin = 1))
	float MaxStamina = 100.f;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Stats|Stamina")
	float Stamina = 100.f;

	/** Stamina regained per second */
	UPROPERTY(EditAnywhere, Category="Stats|Stamina", meta = (ClampMin = 0))
	float StaminaRegenRate = 30.f;

	/** Pause before stamina starts coming back after it was used */
	UPROPERTY(EditAnywhere, Category="Stats|Stamina", meta = (ClampMin = 0, Units = "s"))
	float StaminaRegenDelay = 0.8f;

	/** Longer pause when stamina was used up completely */
	UPROPERTY(EditAnywhere, Category="Stats|Stamina", meta = (ClampMin = 0, Units = "s"))
	float StaminaEmptyRegenDelay = 1.5f;

	bool bIsDead = false;

	/** Regeneration resumes at this time */
	float StaminaRegenResumeTime = 0.f;

	void SetStamina(float NewValue);

	void PauseStaminaRegen();
};
