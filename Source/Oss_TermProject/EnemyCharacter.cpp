// Basic Soulslike melee enemy: notices the player, walks up, attacks with a readable wind-up, flinches when hit, dies

#include "EnemyCharacter.h"
#include "StatsComponent.h"
#include "MeleeHitComponent.h"
#include "AIController.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequenceBase.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	const FName EnemySlot = TEXT("DefaultSlot");
}

AEnemyCharacter::AEnemyCharacter()
{
	PrimaryActorTick.bCanEverTick = true;

	GetCapsuleComponent()->InitCapsuleSize(42.f, 96.f);

	// the player's camera boom must not pull in when an enemy passes between it and the player
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	GetMesh()->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);

	// AI
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	AIControllerClass = AAIController::StaticClass();
	bUseControllerRotationYaw = false;

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->bOrientRotationToMovement = true;
	Movement->RotationRate = FRotator(0.f, 540.f, 0.f);
	Movement->MaxWalkSpeed = ChaseSpeed;

	// same mannequin rig and anim blueprint as the player
	static ConstructorHelpers::FObjectFinder<USkeletalMesh> QuinnMesh(TEXT("/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple.SKM_Quinn_Simple"));
	if (QuinnMesh.Succeeded())
	{
		GetMesh()->SetSkeletalMeshAsset(QuinnMesh.Object);
	}
	static ConstructorHelpers::FClassFinder<UAnimInstance> UnarmedAnimBP(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed"));
	if (UnarmedAnimBP.Succeeded())
	{
		GetMesh()->SetAnimInstanceClass(UnarmedAnimBP.Class);
	}
	GetMesh()->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -96.f), FRotator(0.f, -90.f, 0.f));

	AttackAnimations.Add(TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_01.MM_Attack_01"))));
	AttackAnimations.Add(TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_02.MM_Attack_02"))));
	HeavyAttackAnimation = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_ChargedAttack.MM_ChargedAttack")));
	HitReactAnimation = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Rifle/HitReact/MM_HitReact_Front_Lgt_01.MM_HitReact_Front_Lgt_01")));

	Stats = CreateDefaultSubobject<UStatsComponent>(TEXT("Stats"));

	MeleeHit = CreateDefaultSubobject<UMeleeHitComponent>(TEXT("MeleeHit"));
	MeleeHit->IgnoreTags.Add(TEXT("Enemy"));

	// health bar
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(TEXT("/Engine/BasicShapes/Cube.Cube"));
	auto MakeBarPart = [this](const TCHAR* Name)
	{
		UStaticMeshComponent* Part = CreateDefaultSubobject<UStaticMeshComponent>(Name);
		Part->SetupAttachment(RootComponent);
		Part->SetUsingAbsoluteLocation(true);
		Part->SetUsingAbsoluteRotation(true);
		Part->SetUsingAbsoluteScale(true);
		Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Part->SetGenerateOverlapEvents(false);
		Part->SetCastShadow(false);
		Part->SetHiddenInGame(true);
		if (CubeMesh.Succeeded())
		{
			Part->SetStaticMesh(CubeMesh.Object);
		}
		return Part;
	};
	HealthBarBack = MakeBarPart(TEXT("HealthBarBack"));
	HealthBarFill = MakeBarPart(TEXT("HealthBarFill"));

	// lock-on target, and other enemies' attacks ignore it
	Tags.Add(TEXT("LockOnTarget"));
	Tags.Add(TEXT("Enemy"));
}

void AEnemyCharacter::BeginPlay()
{
	Super::BeginPlay();

	GetCharacterMovement()->MaxWalkSpeed = ChaseSpeed;
	Stats->OnDeath.AddDynamic(this, &AEnemyCharacter::HandleDeath);

	for (TSoftObjectPtr<UAnimSequenceBase>& Anim : AttackAnimations)
	{
		Anim.LoadSynchronous();
	}
	HeavyAttackAnimation.LoadSynchronous();
	HitReactAnimation.LoadSynchronous();

	if (UMaterialInstanceDynamic* MID = HealthBarBack->CreateDynamicMaterialInstance(0))
	{
		MID->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.02f, 0.02f, 0.02f));
	}
	if (UMaterialInstanceDynamic* MID = HealthBarFill->CreateDynamicMaterialInstance(0))
	{
		MID->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.75f, 0.05f, 0.05f));
	}
}

APawn* AEnemyCharacter::GetPlayer() const
{
	APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!Player || !Player->CanBeDamaged())
	{
		return nullptr;
	}

	// ignore a dead player
	if (const UStatsComponent* PlayerStats = Player->FindComponentByClass<UStatsComponent>())
	{
		if (PlayerStats->IsDead())
		{
			return nullptr;
		}
	}
	return Player;
}

bool AEnemyCharacter::CanSee(const APawn* Player) const
{
	FCollisionQueryParams Params(SCENE_QUERY_STAT(EnemySight), false, this);
	FHitResult Hit;
	const FVector Eye = GetActorLocation() + FVector(0.f, 0.f, BaseEyeHeight);
	return !GetWorld()->LineTraceSingleByChannel(Hit, Eye, Player->GetActorLocation(), ECC_Visibility, Params) || Hit.GetActor() == Player;
}

void AEnemyCharacter::FaceTowards(const FVector& Location, float DeltaSeconds, float Speed)
{
	FVector Dir = Location - GetActorLocation();
	Dir.Z = 0.f;
	if (!Dir.IsNearlyZero())
	{
		SetActorRotation(FMath::RInterpTo(GetActorRotation(), Dir.Rotation(), DeltaSeconds, Speed));
	}
}

void AEnemyCharacter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	UpdateHealthBar();

	if (State == EEnemyState::Dead || State == EEnemyState::Stagger)
	{
		return;
	}

	APawn* Player = GetPlayer();
	if (!Player)
	{
		if (State == EEnemyState::Chase)
		{
			State = EEnemyState::Idle;
		}
		return;
	}

	const float Distance = FVector::Dist2D(GetActorLocation(), Player->GetActorLocation());
	const float Now = GetWorld()->GetTimeSeconds();

	switch (State)
	{
	case EEnemyState::Idle:
		if (Distance <= SightRange && CanSee(Player))
		{
			State = EEnemyState::Chase;
			NextAttackTime = Now + FirstAttackDelay;
		}
		break;

	case EEnemyState::Chase:
		if (Distance > LoseSightRange)
		{
			State = EEnemyState::Idle;
			break;
		}
		if (Distance <= AttackRange)
		{
			// in reach: square up, attack when the cooldown is over
			FaceTowards(Player->GetActorLocation(), DeltaSeconds, 8.f);
			if (Now >= NextAttackTime)
			{
				StartAttack();
			}
		}
		else
		{
			// walk straight at the player (no navmesh needed for open arenas)
			FVector Dir = Player->GetActorLocation() - GetActorLocation();
			Dir.Z = 0.f;
			AddMovementInput(Dir.GetSafeNormal());
		}
		break;

	case EEnemyState::Attack:
		// track the player during the wind-up, then commit to the swing direction so it can be dodged
		if (Now - AttackStartTime <= CurrentAttackDuration * AttackTrackingFraction)
		{
			FaceTowards(Player->GetActorLocation(), DeltaSeconds, 6.f);
		}
		break;

	default:
		break;
	}
}

void AEnemyCharacter::StartAttack()
{
	const bool bHeavy = !HeavyAttackAnimation.IsNull() && FMath::FRand() < HeavyAttackChance;
	UAnimSequenceBase* Anim = bHeavy ? HeavyAttackAnimation.Get() : (AttackAnimations.Num() > 0 ? AttackAnimations[FMath::RandRange(0, AttackAnimations.Num() - 1)].Get() : nullptr);
	UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance();
	if (!Anim || !AnimInstance)
	{
		NextAttackTime = GetWorld()->GetTimeSeconds() + 1.f;
		return;
	}

	const float PlayRate = FMath::Max(AttackPlayRate, 0.1f);
	const float BlendOut = 0.2f;
	if (!AnimInstance->PlaySlotAnimationAsDynamicMontage(Anim, EnemySlot, 0.15f, BlendOut, PlayRate))
	{
		NextAttackTime = GetWorld()->GetTimeSeconds() + 1.f;
		return;
	}

	State = EEnemyState::Attack;
	AttackStartTime = GetWorld()->GetTimeSeconds();
	CurrentAttackDuration = Anim->GetPlayLength() / PlayRate;
	GetCharacterMovement()->bOrientRotationToMovement = false;

	// both fists can hit during the window
	TArray<FMeleeHitShape> Shapes;
	for (const TCHAR* Bone : { TEXT("hand_r"), TEXT("hand_l") })
	{
		FMeleeHitShape Shape;
		Shape.Component = GetMesh();
		Shape.Socket = Bone;
		Shape.Radius = FistRadius;
		Shapes.Add(Shape);
	}

	const FVector2D Window = bHeavy ? HeavyAttackHitWindow : AttackHitWindow;
	const float Damage = bHeavy ? HeavyAttackDamage : AttackDamage;
	MeleeHit->EndHitWindow();
	GetWorldTimerManager().SetTimer(HitWindowStartTimer, FTimerDelegate::CreateWeakLambda(this, [this, Shapes, Damage]()
	{
		MeleeHit->BeginHitWindow(Shapes, Damage);
	}), FMath::Max(CurrentAttackDuration * Window.X, 0.01f), false);
	GetWorldTimerManager().SetTimer(HitWindowEndTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		MeleeHit->EndHitWindow();
	}), FMath::Max(CurrentAttackDuration * Window.Y, 0.02f), false);
	GetWorldTimerManager().SetTimer(AttackEndTimer, this, &AEnemyCharacter::EndAttack, FMath::Max(CurrentAttackDuration - BlendOut, 0.1f), false);
}

void AEnemyCharacter::EndAttack()
{
	MeleeHit->EndHitWindow();
	GetCharacterMovement()->bOrientRotationToMovement = true;
	NextAttackTime = GetWorld()->GetTimeSeconds() + FMath::FRandRange(AttackCooldown.X, FMath::Max(AttackCooldown.X, AttackCooldown.Y));
	if (State == EEnemyState::Attack)
	{
		State = EEnemyState::Chase;
	}
}

void AEnemyCharacter::CancelAttack()
{
	GetWorldTimerManager().ClearTimer(AttackEndTimer);
	GetWorldTimerManager().ClearTimer(HitWindowStartTimer);
	GetWorldTimerManager().ClearTimer(HitWindowEndTimer);
	MeleeHit->EndHitWindow();
	GetCharacterMovement()->bOrientRotationToMovement = true;
}

float AEnemyCharacter::TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator, AActor* DamageCauser)
{
	const float Damage = Super::TakeDamage(DamageAmount, DamageEvent, EventInstigator, DamageCauser);
	if (Damage <= 0.f || State == EEnemyState::Dead)
	{
		return 0.f;
	}

	const float Taken = Stats->ApplyDamage(Damage, DamageCauser);
	if (State == EEnemyState::Dead)
	{
		return Taken;
	}

	// flinch: interrupts the attack
	CancelAttack();
	State = EEnemyState::Stagger;
	GetCharacterMovement()->StopMovementImmediately();
	if (DamageCauser)
	{
		FVector Dir = DamageCauser->GetActorLocation() - GetActorLocation();
		Dir.Z = 0.f;
		if (!Dir.IsNearlyZero())
		{
			SetActorRotation(Dir.Rotation());
		}
	}

	UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance();
	if (UAnimSequenceBase* Anim = HitReactAnimation.Get())
	{
		if (AnimInstance)
		{
			AnimInstance->PlaySlotAnimationAsDynamicMontage(Anim, EnemySlot, 0.05f, 0.2f);
		}
	}
	else if (AnimInstance)
	{
		AnimInstance->StopSlotAnimation(0.1f, EnemySlot);
	}

	GetWorldTimerManager().SetTimer(StaggerTimer, this, &AEnemyCharacter::EndStagger, FMath::Max(HitStaggerTime, 0.01f), false);
	return Taken;
}

void AEnemyCharacter::EndStagger()
{
	if (State != EEnemyState::Stagger)
	{
		return;
	}

	// being hit always makes it fight back
	State = EEnemyState::Chase;
	NextAttackTime = FMath::Max(NextAttackTime, GetWorld()->GetTimeSeconds() + 0.3f);
}

void AEnemyCharacter::HandleDeath(AActor* DamageCauser)
{
	State = EEnemyState::Dead;
	CancelAttack();
	GetWorldTimerManager().ClearTimer(StaggerTimer);

	// no longer a target
	Tags.Remove(TEXT("LockOnTarget"));
	HealthBarBack->SetHiddenInGame(true);
	HealthBarFill->SetHiddenInGame(true);

	if (AController* AI = GetController())
	{
		AI->UnPossess();
	}

	// ragdoll
	GetCharacterMovement()->DisableMovement();
	GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	GetMesh()->SetCollisionProfileName(TEXT("Ragdoll"));
	GetMesh()->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	GetMesh()->SetSimulatePhysics(true);

	SetLifeSpan(CorpseLifeSpan);
}

void AEnemyCharacter::UpdateHealthBar()
{
	const bool bShow = State != EEnemyState::Dead && Stats->GetHealth() < Stats->GetMaxHealth();
	HealthBarBack->SetHiddenInGame(!bShow);
	HealthBarFill->SetHiddenInGame(!bShow);
	if (!bShow)
	{
		return;
	}

	APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0);
	const FVector Center = GetActorLocation() + FVector(0.f, 0.f, HealthBarHeight);
	const FVector ToCamera = Camera ? (Camera->GetCameraLocation() - Center) : -GetActorForwardVector();
	const FRotator Facing(0.f, ToCamera.Rotation().Yaw, 0.f);
	const FVector Right = FRotationMatrix(Facing).GetUnitAxis(EAxis::Y);

	const float Pct = FMath::Clamp(Stats->GetHealth() / Stats->GetMaxHealth(), 0.f, 1.f);
	const float Width = HealthBarSize.X;
	const float Height = HealthBarSize.Y;

	// engine cube is 100cm: X = depth (toward the camera), Y = width, Z = height
	HealthBarBack->SetWorldLocationAndRotation(Center, Facing);
	HealthBarBack->SetWorldScale3D(FVector(0.01f, (Width + 2.f) / 100.f, (Height + 2.f) / 100.f));

	// fill stays anchored at the left end as seen from the camera (the facing frame's +Y is the viewer's left)
	const float FillWidth = FMath::Max(Width * Pct, 0.01f);
	const FVector FillCenter = Center + Right * (Width - FillWidth) * 0.5f + Facing.Vector() * 1.f;
	HealthBarFill->SetWorldLocationAndRotation(FillCenter, Facing);
	HealthBarFill->SetWorldScale3D(FVector(0.01f, FillWidth / 100.f, Height / 100.f));
}
