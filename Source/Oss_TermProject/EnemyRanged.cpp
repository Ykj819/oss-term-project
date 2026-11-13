// Ranged enemy: keeps its distance and throws rocks in an arc; backs off when the player closes in, shoves when cornered

#include "EnemyRanged.h"
#include "EnemyProjectile.h"
#include "StatsComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	const FName RangedSlot = TEXT("DefaultSlot");
	const FName RockHandBone = TEXT("middle_metacarpal_r");
	const FName RockHandFallbackBone = TEXT("hand_r");
}

AEnemyRanged::AEnemyRanged()
{
	ProjectileClass = AEnemyProjectile::StaticClass();

	ThrowAnimation = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Throw.MM_Throw")));
	FallbackThrowAnimation = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_02.MM_Attack_02")));

	// weaker and quicker to give up than the melee enemy; the shove is a light push, not a real attack
	SightRange = 2200.f;
	LoseSightRange = 3000.f;
	AttackRange = ShoveRange;
	ChaseSpeed = 280.f;
	AttackDamage = 8.f;
	HeavyAttackChance = 0.f;
	AttackCooldown = FVector2D(1.5f, 2.5f);
	FirstAttackDelay = 0.8f;
	SoulReward = 12;

	bTintBody = true;
	BodyTint = FLinearColor(0.35f, 0.24f, 0.12f);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphereMesh(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(TEXT("/Engine/BasicShapes/Cube.Cube"));

	HeldRock = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("HeldRock"));
	HeldRock->SetupAttachment(GetMesh(), RockHandBone);
	HeldRock->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	HeldRock->SetGenerateOverlapEvents(false);
	HeldRock->SetCanEverAffectNavigation(false);
	HeldRock->SetRelativeScale3D(FVector(0.2f, 0.17f, 0.15f));
	HeldRock->SetHiddenInGame(true);
	if (SphereMesh.Succeeded())
	{
		HeldRock->SetStaticMesh(SphereMesh.Object);
	}

	Pouch = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Pouch"));
	Pouch->SetupAttachment(GetMesh(), TEXT("pelvis"));
	Pouch->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Pouch->SetGenerateOverlapEvents(false);
	Pouch->SetCanEverAffectNavigation(false);
	Pouch->SetRelativeLocation(FVector(0.f, 4.f, -18.f));
	Pouch->SetRelativeScale3D(FVector(0.14f, 0.2f, 0.18f));
	if (SphereMesh.Succeeded())
	{
		Pouch->SetStaticMesh(SphereMesh.Object);
	}
}

void AEnemyRanged::BeginPlay()
{
	Super::BeginPlay();

	if (UStatsComponent* EnemyStats = FindComponentByClass<UStatsComponent>())
	{
		EnemyStats->SetMaxHealth(MaxHealth);
		EnemyStats->RestoreAll();
	}

	ThrowAnimation.LoadSynchronous();
	FallbackThrowAnimation.LoadSynchronous();

	// palm bone may be missing on some mannequin meshes
	if (!GetMesh()->DoesSocketExist(RockHandBone))
	{
		HeldRock->AttachToComponent(GetMesh(), FAttachmentTransformRules::KeepRelativeTransform, RockHandFallbackBone);
	}

	if (UMaterialInstanceDynamic* MID = HeldRock->CreateDynamicMaterialInstance(0))
	{
		MID->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.09f, 0.08f, 0.07f));
	}
	if (UMaterialInstanceDynamic* MID = Pouch->CreateDynamicMaterialInstance(0))
	{
		MID->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.12f, 0.07f, 0.03f));
	}
}

void AEnemyRanged::TickCombat(APawn* Player, float Distance, float Now, float DeltaSeconds)
{
	UCharacterMovementComponent* Movement = GetCharacterMovement();

	if (State == EEnemyState::Attack)
	{
		if (bThrowing)
		{
			// aims during the wind-up, then the throw direction is locked in
			if (Now < ThrowReleaseTime)
			{
				FaceTowards(Player->GetActorLocation(), DeltaSeconds, 7.f);
			}
			return;
		}

		// melee shove
		Super::TickCombat(Player, Distance, Now, DeltaSeconds);
		return;
	}

	if (State != EEnemyState::Chase)
	{
		return;
	}

	if (Distance > LoseSightRange)
	{
		StopRetreat(Now);
		State = EEnemyState::Idle;
		return;
	}

	FVector ToPlayer = Player->GetActorLocation() - GetActorLocation();
	ToPlayer.Z = 0.f;
	const FVector ToPlayerDir = ToPlayer.GetSafeNormal();

	// ---- backing off ----
	if (bRetreating)
	{
		const bool bFarEnough = Distance >= PreferredRange;
		const bool bTooLong = Now - RetreatStartTime >= MaxRetreatTime;
		const FVector Away = GetActorLocation() - ToPlayerDir * 100.f;
		const bool bLeashed = FVector::Dist2D(Away, HomeTransform.GetLocation()) > LeashRadius;
		if (bFarEnough || bTooLong || bLeashed || Distance <= ShoveRange)
		{
			StopRetreat(Now);
		}
		else
		{
			AddMovementInput(-ToPlayerDir);
			return;
		}
	}

	// ---- cornered: shove ----
	if (Distance <= ShoveRange)
	{
		FaceTowards(Player->GetActorLocation(), DeltaSeconds, 8.f);
		if (Now >= NextAttackTime)
		{
			StartAttack();
		}
		return;
	}

	// ---- too close: start backing off (not every time, so it also stands and fights) ----
	if (Distance < RetreatRange && Now >= NextRetreatTime)
	{
		const FVector Away = GetActorLocation() - ToPlayerDir * 100.f;
		if (FVector::Dist2D(Away, HomeTransform.GetLocation()) <= LeashRadius)
		{
			bRetreating = true;
			RetreatStartTime = Now;
			Movement->MaxWalkSpeed = RetreatSpeed;
			AddMovementInput(-ToPlayerDir);
			return;
		}
	}

	// ---- out of range / no clear shot: walk closer ----
	if (Distance > ThrowRange || !CanSee(Player))
	{
		Movement->bOrientRotationToMovement = true;
		AddMovementInput(ToPlayerDir);
		return;
	}

	// ---- in range: hold ground, face the player, throw on cooldown ----
	FaceTowards(Player->GetActorLocation(), DeltaSeconds, 6.f);
	if (Now >= NextAttackTime)
	{
		StartThrow(Player);
	}
}

void AEnemyRanged::StopRetreat(float Now)
{
	if (!bRetreating)
	{
		return;
	}
	bRetreating = false;
	NextRetreatTime = Now + RetreatCooldown;
	GetCharacterMovement()->MaxWalkSpeed = ChaseSpeed;
}

void AEnemyRanged::StartThrow(APawn* Player)
{
	UAnimSequenceBase* Anim = ThrowAnimation.Get() ? ThrowAnimation.Get() : FallbackThrowAnimation.Get();
	UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance();
	const float Now = GetWorld()->GetTimeSeconds();
	if (!Anim || !AnimInstance)
	{
		NextAttackTime = Now + 1.f;
		return;
	}

	const float PlayRate = FMath::Max(ThrowPlayRate, 0.1f);
	const float BlendOut = 0.2f;
	if (!AnimInstance->PlaySlotAnimationAsDynamicMontage(Anim, RangedSlot, 0.15f, BlendOut, PlayRate))
	{
		NextAttackTime = Now + 1.f;
		return;
	}

	State = EEnemyState::Attack;
	bThrowing = true;
	GetCharacterMovement()->StopMovementImmediately();
	GetCharacterMovement()->bOrientRotationToMovement = false;

	AttackStartTime = Now;
	CurrentAttackDuration = Anim->GetPlayLength() / PlayRate;
	const float ReleaseDelay = FMath::Max(CurrentAttackDuration * ThrowReleaseFraction, 0.05f);
	ThrowReleaseTime = Now + ReleaseDelay;

	// rock appears in the hand: the wind-up is the warning
	HeldRock->SetHiddenInGame(false);

	GetWorldTimerManager().SetTimer(ThrowReleaseTimer, this, &AEnemyRanged::ReleaseRock, ReleaseDelay, false);
	GetWorldTimerManager().SetTimer(ThrowEndTimer, this, &AEnemyRanged::EndThrow, FMath::Max(CurrentAttackDuration - BlendOut, ReleaseDelay + 0.05f), false);
}

void AEnemyRanged::ReleaseRock()
{
	HeldRock->SetHiddenInGame(true);

	APawn* Player = GetPlayer();
	if (!Player || !ProjectileClass)
	{
		return;
	}

	const FVector Start = HeldRock->GetComponentLocation();
	const float GravityZ = GetWorld()->GetGravityZ() * RockGravityScale;

	// aim at the chest, partly leading a moving target
	const FVector PlayerVelocity = Player->GetVelocity();
	FVector Target = Player->GetActorLocation() + FVector(0.f, 0.f, 20.f);
	const float FlightTime = FVector::Dist(Start, Target) / FMath::Max(ThrowSpeed, 1.f);
	Target += FVector(PlayerVelocity.X, PlayerVelocity.Y, 0.f) * FlightTime * ThrowLead;

	FVector LaunchVelocity;
	const bool bSolved = UGameplayStatics::SuggestProjectileVelocity(this, LaunchVelocity, Start, Target, ThrowSpeed,
		false, 0.f, GravityZ, ESuggestProjVelocityTraceOption::DoNotTrace);
	if (!bSolved)
	{
		// out of reach at this speed: throw at 45 degrees toward it
		FVector Flat = Target - Start;
		Flat.Z = 0.f;
		LaunchVelocity = (Flat.GetSafeNormal() + FVector::UpVector).GetSafeNormal() * ThrowSpeed;
	}

	FActorSpawnParameters Params;
	Params.Owner = this;
	Params.Instigator = this;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	if (AEnemyProjectile* Rock = GetWorld()->SpawnActor<AEnemyProjectile>(ProjectileClass, Start, LaunchVelocity.Rotation(), Params))
	{
		Rock->Launch(LaunchVelocity, GravityZ, ThrowDamage);
	}
}

void AEnemyRanged::EndThrow()
{
	bThrowing = false;
	HeldRock->SetHiddenInGame(true);
	GetCharacterMovement()->bOrientRotationToMovement = true;
	NextAttackTime = GetWorld()->GetTimeSeconds() + FMath::FRandRange(ThrowCooldown.X, FMath::Max(ThrowCooldown.X, ThrowCooldown.Y));
	if (State == EEnemyState::Attack)
	{
		State = EEnemyState::Chase;
	}
}

void AEnemyRanged::CancelAttack()
{
	Super::CancelAttack();

	GetWorldTimerManager().ClearTimer(ThrowReleaseTimer);
	GetWorldTimerManager().ClearTimer(ThrowEndTimer);
	bThrowing = false;
	if (HeldRock)
	{
		HeldRock->SetHiddenInGame(true);
	}

	bRetreating = false;
	GetCharacterMovement()->MaxWalkSpeed = ChaseSpeed;
}
