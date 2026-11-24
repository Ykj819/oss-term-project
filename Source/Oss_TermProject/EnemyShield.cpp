// Shield enemy (plush bear, darker): holds an iron tower shield in both hands, its only attack is a short shield rush; stands still for a while after each rush (the opening)

#include "EnemyShield.h"
#include "StatsComponent.h"
#include "MeleeHitComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

AEnemyShield::AEnemyShield()
{
	// slow and heavy; the rush is its only attack
	ChaseSpeed = 220.f;
	SightRange = 1500.f;
	AttackRange = ChargeStartRange;
	FirstAttackDelay = 0.6f;
	SoulReward = 20;

	// hits don't make it flinch: the pause after the rush is the opening, not the hit
	bFlinchOnHit = false;

	bTintBody = true;
	BodyTint = FLinearColor(0.5f, 0.45f, 0.42f);	// same plush bear, darker

	static ConstructorHelpers::FObjectFinder<UStaticMesh> ShieldMesh(TEXT("/Game/Characters/Enemies/Meshes/SM_EnemyShield.SM_EnemyShield"));
	const FString ShieldAnimDir = TEXT("/Game/Characters/Mannequins/Anims/Shield/");
	auto ShieldAnim = [&ShieldAnimDir](const TCHAR* Name)
	{
		return TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(ShieldAnimDir + Name + TEXT(".") + Name));
	};
	HoldAnim = ShieldAnim(TEXT("MM_Shield_Hold"));
	BraceAnim = ShieldAnim(TEXT("MM_Shield_Brace"));
	PushAnim = ShieldAnim(TEXT("MM_Shield_Push"));
	// no fist attacks / hit react: the arms stay on the shield
	AttackAnimations.Reset();
	HeavyAttackAnimation.Reset();

	// held in front of the chest, follows the body's facing
	Shield = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Shield"));
	Shield->SetupAttachment(RootComponent);
	Shield->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Shield->SetGenerateOverlapEvents(false);
	Shield->SetCanEverAffectNavigation(false);
	Shield->SetRelativeLocation(FVector(ShieldForward.X, 0.f, ShieldLift.X));
	Shield->SetRelativeScale3D(ShieldSize / FVector(10.f, 80.f, 110.f));
	if (ShieldMesh.Succeeded())
	{
		Shield->SetStaticMesh(ShieldMesh.Object);
	}
}

void AEnemyShield::BeginPlay()
{
	Super::BeginPlay();

	if (UStatsComponent* EnemyStats = FindComponentByClass<UStatsComponent>())
	{
		EnemyStats->SetMaxHealth(MaxHealth);
		EnemyStats->RestoreAll();
	}

	AttackRange = ChargeStartRange;
	SavedMaxAcceleration = GetCharacterMovement()->MaxAcceleration;

	Shield->SetRelativeLocation(FVector(ShieldForward.X, 0.f, ShieldLift.X));
	Shield->SetRelativeScale3D(ShieldSize / FVector(10.f, 80.f, 110.f));
	ShieldMID = Shield->CreateDynamicMaterialInstance(0);
	if (ShieldMID)
	{
		ShieldMID->SetVectorParameterValue(TEXT("Color"), ShieldColor);
	}

	for (TSoftObjectPtr<UAnimSequenceBase>* Anim : { &HoldAnim, &BraceAnim, &PushAnim })
	{
		Anim->LoadSynchronous();
	}
	PlayShieldPose(HoldAnim, 0.f);
}

void AEnemyShield::ResetEnemy()
{
	Super::ResetEnemy();
	PlayShieldPose(HoldAnim, 0.f);	// the reset stopped every montage
}

void AEnemyShield::PlayShieldPose(const TSoftObjectPtr<UAnimSequenceBase>& Anim, float BlendTime)
{
	UAnimInstance* AnimInstance = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr;
	UAnimSequenceBase* Sequence = Anim.Get();
	if (AnimInstance && Sequence)
	{
		AnimInstance->PlaySlotAnimationAsDynamicMontage(Sequence, HoldSlotName, BlendTime, BlendTime, 1.f, 100000);
	}
}

float AEnemyShield::TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator, AActor* DamageCauser)
{
	if (State != EEnemyState::Dead && DamageCauser && DamageCauser != this)
	{
		FVector ToAttacker = DamageCauser->GetActorLocation() - GetActorLocation();
		ToAttacker.Z = 0.f;
		FVector Forward = GetActorForwardVector();
		Forward.Z = 0.f;

		const float CosAngle = FVector::DotProduct(ToAttacker.GetSafeNormal(), Forward.GetSafeNormal());
		if (!ToAttacker.IsNearlyZero() && CosAngle >= FMath::Cos(FMath::DegreesToRadians(BlockHalfAngle)))
		{
			// blocked: shield flashes, no damage
			if (ShieldMID)
			{
				ShieldMID->SetVectorParameterValue(TEXT("Color"), BlockFlashColor);
				ShieldMID->SetScalarParameterValue(TEXT("Flash"), BlockFlashGlow);
				GetWorldTimerManager().SetTimer(BlockFlashTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
				{
					if (ShieldMID)
					{
						ShieldMID->SetVectorParameterValue(TEXT("Color"), ShieldColor);
						ShieldMID->SetScalarParameterValue(TEXT("Flash"), 0.f);
					}
				}), 0.12f, false);
			}
			return 0.f;
		}
	}

	return Super::TakeDamage(DamageAmount, DamageEvent, EventInstigator, DamageCauser);
}

void AEnemyShield::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	// shield follows the hands: pulled in during the wind-up (MM_Shield_Brace), shoved out in the rush (MM_Shield_Push)
	FVector2D Target(ShieldForward.X, ShieldLift.X);
	if (Phase == EShieldChargePhase::WindUp)
	{
		Target = FVector2D(ShieldForward.Y, ShieldLift.Y);
	}
	else if (Phase == EShieldChargePhase::Dash)
	{
		Target = FVector2D(ShieldForward.Z, ShieldLift.Z);
	}
	const FVector Current = Shield->GetRelativeLocation();
	const float Speed = Phase == EShieldChargePhase::Dash ? 20.f : 7.f;
	Shield->SetRelativeLocation(FVector(FMath::FInterpTo(Current.X, Target.X, DeltaSeconds, Speed), 0.f,
		FMath::FInterpTo(Current.Z, Target.Y, DeltaSeconds, Speed)));

	// the rush keeps going even if the player drops out of sight mid-dash
	if (Phase == EShieldChargePhase::Dash && State != EEnemyState::Dead)
	{
		AddMovementInput(DashDirection);
	}
}

void AEnemyShield::TickCombat(APawn* Player, float Distance, float Now, float DeltaSeconds)
{
	if (State == EEnemyState::Attack)
	{
		// aims only during the wind-up; the rush direction and the pause are fixed
		if (Phase == EShieldChargePhase::WindUp)
		{
			FaceTowards(Player->GetActorLocation(), DeltaSeconds, 8.f);
		}
		return;
	}

	if (State != EEnemyState::Chase)
	{
		return;
	}

	if (Distance > LoseSightRange)
	{
		State = EEnemyState::Idle;
		return;
	}

	if (Distance <= ChargeStartRange && CanSee(Player))
	{
		FaceTowards(Player->GetActorLocation(), DeltaSeconds, 8.f);
		if (Now >= NextAttackTime)
		{
			StartWindUp();
		}
		return;
	}

	// walk straight at the player
	FVector Dir = Player->GetActorLocation() - GetActorLocation();
	Dir.Z = 0.f;
	AddMovementInput(Dir.GetSafeNormal());
}

void AEnemyShield::StartWindUp()
{
	State = EEnemyState::Attack;
	Phase = EShieldChargePhase::WindUp;
	AttackStartTime = GetWorld()->GetTimeSeconds();

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->StopMovementImmediately();
	Movement->bOrientRotationToMovement = false;

	PlayShieldPose(BraceAnim, 0.3f);

	GetWorldTimerManager().SetTimer(PhaseTimer, this, &AEnemyShield::StartDash, FMath::Max(WindUpTime, 0.05f), false);
}

void AEnemyShield::StartDash()
{
	Phase = EShieldChargePhase::Dash;

	FVector Forward = GetActorForwardVector();
	Forward.Z = 0.f;
	DashDirection = Forward.GetSafeNormal();

	// instant top speed in the facing direction
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->MaxWalkSpeed = DashSpeed;
	Movement->MaxAcceleration = 100000.f;
	Movement->Velocity = DashDirection * DashSpeed;
	PlayShieldPose(PushAnim, 0.08f);

	// the shield face is the hitbox (segment along its height, sphere wide enough to cover its width)
	FMeleeHitShape Shape;
	Shape.Component = Shield;
	Shape.Start = FVector(0.f, 0.f, -40.f);
	Shape.End = FVector(0.f, 0.f, 40.f);
	Shape.Radius = ShieldSize.Y * 0.5f + 5.f;

	if (UMeleeHitComponent* Hit = FindComponentByClass<UMeleeHitComponent>())
	{
		Hit->EndHitWindow();
		Hit->BeginHitWindow({ Shape }, ChargeDamage);
	}

	GetWorldTimerManager().SetTimer(PhaseTimer, this, &AEnemyShield::StartRecover, FMath::Max(DashTime, 0.05f), false);
}

void AEnemyShield::StartRecover()
{
	Phase = EShieldChargePhase::Recover;
	PlayShieldPose(HoldAnim, 0.4f);

	if (UMeleeHitComponent* Hit = FindComponentByClass<UMeleeHitComponent>())
	{
		Hit->EndHitWindow();
	}
	RestoreMovement();
	GetCharacterMovement()->StopMovementImmediately();
	GetCharacterMovement()->bOrientRotationToMovement = false;

	// stands still: no turning, no walking
	GetWorldTimerManager().SetTimer(PhaseTimer, this, &AEnemyShield::FinishCharge, FMath::Max(RecoverTime, 0.01f), false);
}

void AEnemyShield::FinishCharge()
{
	Phase = EShieldChargePhase::None;
	GetCharacterMovement()->bOrientRotationToMovement = true;
	NextAttackTime = GetWorld()->GetTimeSeconds() + 0.3f;
	if (State == EEnemyState::Attack)
	{
		State = EEnemyState::Chase;
	}
}

void AEnemyShield::RestoreMovement()
{
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->MaxWalkSpeed = ChaseSpeed;
	if (SavedMaxAcceleration > 0.f)
	{
		Movement->MaxAcceleration = SavedMaxAcceleration;
	}
}

void AEnemyShield::CancelAttack()
{
	Super::CancelAttack();

	// death / reset in the middle of a charge
	GetWorldTimerManager().ClearTimer(PhaseTimer);
	Phase = EShieldChargePhase::None;
	RestoreMovement();
	PlayShieldPose(HoldAnim, 0.2f);
}
