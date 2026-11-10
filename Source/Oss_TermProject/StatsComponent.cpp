// Health and stamina for the player (and later enemies)

#include "StatsComponent.h"
#include "Engine/World.h"

UStatsComponent::UStatsComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
}

void UStatsComponent::BeginPlay()
{
	Super::BeginPlay();

	Health = MaxHealth;
	Stamina = MaxStamina;
	OnHealthChanged.Broadcast(Health, MaxHealth);
	OnStaminaChanged.Broadcast(Stamina, MaxStamina);
}

void UStatsComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	if (!bIsDead && Stamina < MaxStamina && GetWorld()->GetTimeSeconds() >= StaminaRegenResumeTime)
	{
		SetStamina(Stamina + StaminaRegenRate * DeltaTime);
	}
}

float UStatsComponent::ApplyDamage(float Amount, AActor* DamageCauser)
{
	if (bIsDead || Amount <= 0.f)
	{
		return 0.f;
	}

	const float OldHealth = Health;
	Health = FMath::Max(Health - Amount, 0.f);
	OnHealthChanged.Broadcast(Health, MaxHealth);

	if (Health <= 0.f)
	{
		bIsDead = true;
		OnDeath.Broadcast(DamageCauser);
	}

	return OldHealth - Health;
}

void UStatsComponent::Heal(float Amount)
{
	if (bIsDead || Amount <= 0.f)
	{
		return;
	}

	Health = FMath::Min(Health + Amount, MaxHealth);
	OnHealthChanged.Broadcast(Health, MaxHealth);
}

void UStatsComponent::RestoreAll()
{
	bIsDead = false;
	Health = MaxHealth;
	OnHealthChanged.Broadcast(Health, MaxHealth);
	SetStamina(MaxStamina);
}

bool UStatsComponent::ConsumeStamina(float Amount)
{
	if (!HasStamina())
	{
		return false;
	}

	SetStamina(Stamina - Amount);
	PauseStaminaRegen();
	return true;
}

void UStatsComponent::DrainStamina(float AmountPerSecond, float DeltaTime)
{
	if (!HasStamina())
	{
		return;
	}

	SetStamina(Stamina - AmountPerSecond * DeltaTime);
	PauseStaminaRegen();
}

void UStatsComponent::SetStamina(float NewValue)
{
	NewValue = FMath::Clamp(NewValue, 0.f, MaxStamina);
	if (NewValue != Stamina)
	{
		Stamina = NewValue;
		OnStaminaChanged.Broadcast(Stamina, MaxStamina);
	}
}

void UStatsComponent::PauseStaminaRegen()
{
	StaminaRegenResumeTime = GetWorld()->GetTimeSeconds() + (Stamina <= 0.f ? StaminaEmptyRegenDelay : StaminaRegenDelay);
}
