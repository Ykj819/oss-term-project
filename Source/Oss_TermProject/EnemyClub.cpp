// Club giant: the basic enemy at 1.5x size with a huge two-handed club. Slow, heavy, readable swings; super armor (hits never flinch it).

#include "EnemyClub.h"
#include "StatsComponent.h"
#include "MeleeHitComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr float BaseRadius = 42.f;
	constexpr float BaseHalfHeight = 96.f;
	const FName AttackSlot = TEXT("DefaultSlot");

	TSoftObjectPtr<UAnimSequenceBase> ClubAnim(const TCHAR* Name)
	{
		return TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(FString::Printf(TEXT("/Game/Characters/Mannequins/Anims/Club/%s.%s"), Name, Name)));
	}
}

AEnemyClub::AEnemyClub()
{
	const float S = SizeScale;
	GetCapsuleComponent()->InitCapsuleSize(BaseRadius * S, BaseHalfHeight * S);
	GetMesh()->SetRelativeLocation(FVector(0.f, 0.f, -BaseHalfHeight * S));
	GetMesh()->SetRelativeScale3D(FVector(S));

	// plush bunny (mannequin skeleton) instead of the base class's bear
	static ConstructorHelpers::FObjectFinder<USkeletalMesh> BunnyMesh(TEXT("/Game/Characters/Enemies/Meshes/SKM_PlushBunny.SKM_PlushBunny"));
	if (BunnyMesh.Succeeded())
	{
		GetMesh()->SetSkeletalMeshAsset(BunnyMesh.Object);
	}

	// heavy and slow; hits don't interrupt it (super armor)
	bFlinchOnHit = false;
	ChaseSpeed = 220.f;
	GetCharacterMovement()->MaxWalkSpeed = ChaseSpeed;
	GetCharacterMovement()->RotationRate = FRotator(0.f, 300.f, 0.f);
	AttackRange = 260.f;
	AttackPlayRate = 1.f;
	AttackCooldown = FVector2D(1.f, 2.2f);
	FirstAttackDelay = 0.6f;
	SightRange = 1500.f;
	LoseSightRange = 2500.f;
	SoulReward = 40;
	HealthBarHeight = 190.f;
	HealthBarSize = FVector2D(130.f, 9.f);
	bTintBody = true;
	BodyTint = FLinearColor(1.f, 1.f, 1.f);	// plush bunny mesh: white from its vertex colours

	// no fist attacks
	AttackAnimations.Reset();
	HeavyAttackAnimation.Reset();

	IdleAnim = ClubAnim(TEXT("MM_Club_Idle"));
	SweepAnim = ClubAnim(TEXT("MM_Club_Sweep"));
	SweepBackAnim = ClubAnim(TEXT("MM_Club_Sweep_Back"));
	SlamAnim = ClubAnim(TEXT("MM_Club_Slam"));

	// ---- club: wooden bat SM_ClubBat along ClubRoot's Z (mesh origin = right-hand grip, 160 cm long, grip 30 cm from the knob;
	// made by Export/Blender/scripts/props/gen_enemy_props.py). The hand closes around it (mitten hands, the bat passes through) ----
	ClubRoot = CreateDefaultSubobject<USceneComponent>(TEXT("ClubRoot"));
	ClubRoot->SetupAttachment(GetMesh(), TEXT("hand_r"));

	static ConstructorHelpers::FObjectFinder<UStaticMesh> BatMesh(TEXT("/Game/Characters/Enemies/Meshes/SM_ClubBat.SM_ClubBat"));
	UStaticMeshComponent* Bat = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ClubBat"));
	Bat->SetupAttachment(ClubRoot);
	Bat->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Bat->SetGenerateOverlapEvents(false);
	Bat->SetCanEverAffectNavigation(false);
	if (BatMesh.Succeeded())
	{
		Bat->SetStaticMesh(BatMesh.Object);
	}
	// the mesh is 160 cm with the grip 30 cm from the end: stretch along Z if ClubLength is changed
	Bat->SetRelativeScale3D(FVector(1.f, 1.f, ClubLength / 160.f));
	ClubParts.Add(Bat);
}
void AEnemyClub::BeginPlay()
{
	// size first: the base class remembers the mesh setup for resets
	const float S = SizeScale;
	GetCapsuleComponent()->SetCapsuleSize(BaseRadius * S, BaseHalfHeight * S);
	GetMesh()->SetRelativeLocation(FVector(0.f, 0.f, -BaseHalfHeight * S));
	GetMesh()->SetRelativeScale3D(FVector(S));

	Super::BeginPlay();

	if (UStatsComponent* EnemyStats = FindComponentByClass<UStatsComponent>())
	{
		EnemyStats->SetMaxHealth(MaxHealth);
		EnemyStats->RestoreAll();
	}

	for (TSoftObjectPtr<UAnimSequenceBase>* Anim : { &IdleAnim, &SweepAnim, &SweepBackAnim, &SlamAnim })
	{
		Anim->LoadSynchronous();
	}

	// placed actors saved this array when it held the old engine-shape parts (now deleted -> null entries): rebuild it
	ClubParts.Reset();
	{
		TInlineComponentArray<UStaticMeshComponent*> Comps(this);
		for (UStaticMeshComponent* Comp : Comps)
		{
			if (Comp && Comp->GetFName() == TEXT("ClubBat"))
			{
				ClubParts.Add(Comp);
			}
		}
	}

	for (UStaticMeshComponent* Part : ClubParts)
	{
		if (UMaterialInstanceDynamic* MID = Part->CreateDynamicMaterialInstance(0))
		{
			MID->SetVectorParameterValue(TEXT("Color"), ClubColor);
		}
	}

	AttachClub();
	PlayHoldLoop();
}

void AEnemyClub::AttachClub()
{
	USkeletalMesh* SkelMesh = GetMesh()->GetSkeletalMeshAsset();
	if (!SkelMesh)
	{
		return;
	}

	// same grip as the player's stick, worked out in the reference pose: the club runs along the knuckle line (pinky -> index)
	const FReferenceSkeleton& RefSkel = SkelMesh->GetRefSkeleton();
	auto RefComponentSpace = [&RefSkel](FName Bone) -> FTransform
	{
		FTransform Result = FTransform::Identity;
		for (int32 Index = RefSkel.FindBoneIndex(Bone); Index != INDEX_NONE; Index = RefSkel.GetParentIndex(Index))
		{
			Result = Result * RefSkel.GetRefBonePose()[Index];
		}
		return Result;
	};
	if (RefSkel.FindBoneIndex(TEXT("hand_r")) == INDEX_NONE)
	{
		return;
	}

	const FTransform Hand = RefComponentSpace(TEXT("hand_r"));
	const FVector Index = RefComponentSpace(TEXT("index_01_r")).GetLocation();
	const FVector Middle = RefComponentSpace(TEXT("middle_01_r")).GetLocation();
	const FVector Pinky = RefComponentSpace(TEXT("pinky_01_r")).GetLocation();
	const FVector Axis = (Index - Pinky).GetSafeNormal();
	const FVector Grip = FMath::Lerp(Hand.GetLocation(), Middle, 0.6f);

	// relative to the (unscaled) bone: the mesh's SizeScale scales the club with the body
	const FTransform ClubComponentSpace(FRotationMatrix::MakeFromZ(Axis).ToQuat(), Grip);
	ClubRoot->SetRelativeTransform(ClubComponentSpace.GetRelativeTransform(Hand));
}

void AEnemyClub::PlayHoldLoop()
{
	UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance();
	UAnimSequenceBase* Anim = IdleAnim.Get();
	if (AnimInstance && Anim)
	{
		AnimInstance->PlaySlotAnimationAsDynamicMontage(Anim, HoldSlotName, 0.3f, 0.3f, 1.f, 100000);
	}
}

void AEnemyClub::TickCombat(APawn* Player, float Distance, float Now, float DeltaSeconds)
{
	switch (State)
	{
	case EEnemyState::Chase:
		if (Distance > LoseSightRange)
		{
			State = EEnemyState::Idle;
			break;
		}
		if (Distance <= AttackRange)
		{
			FaceTowards(Player->GetActorLocation(), DeltaSeconds, 4.f);
			if (Now >= NextAttackTime)
			{
				if (FMath::FRand() < SlamChance)
				{
					StartClubAttack(EClubAttack::Slam);
				}
				else
				{
					bComboQueued = FMath::FRand() < ComboChance;
					StartClubAttack(EClubAttack::Sweep);
				}
			}
		}
		else
		{
			FVector Dir = Player->GetActorLocation() - GetActorLocation();
			Dir.Z = 0.f;
			AddMovementInput(Dir.GetSafeNormal());
		}
		break;

	case EEnemyState::Attack:
		// turns with the player during the wind-up, then the swing is committed (step out of it / roll through it)
		if (Now - AttackStartTime <= CurrentTrackTime)
		{
			FaceTowards(Player->GetActorLocation(), DeltaSeconds, 4.f);
		}
		break;

	default:
		break;
	}
}

void AEnemyClub::StartClubAttack(EClubAttack Attack)
{
	const TSoftObjectPtr<UAnimSequenceBase>* Anim = nullptr;
	FVector2D Window;
	float Damage = 0.f;
	float Track = 0.f;
	switch (Attack)
	{
	case EClubAttack::Sweep:		Anim = &SweepAnim;		Window = SweepHitWindow;		Damage = SweepDamage;	Track = SweepTrackFraction; break;
	case EClubAttack::SweepBack:	Anim = &SweepBackAnim;	Window = SweepBackHitWindow;	Damage = SweepDamage;	Track = SweepBackTrackFraction; break;
	case EClubAttack::Slam:			Anim = &SlamAnim;		Window = SlamHitWindow;			Damage = SlamDamage;	Track = SlamTrackFraction; break;
	default: return;
	}

	UAnimSequenceBase* Sequence = Anim->Get();
	UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance();
	const float Rate = FMath::Max(AttackPlayRate, 0.1f);
	const bool bChained = Attack == EClubAttack::SweepBack;
	const float BlendOut = 0.3f;
	if (!Sequence || !AnimInstance || !AnimInstance->PlaySlotAnimationAsDynamicMontage(Sequence, AttackSlot, bChained ? 0.1f : 0.25f, BlendOut, Rate))
	{
		NextAttackTime = GetWorld()->GetTimeSeconds() + 1.f;
		return;
	}

	FTimerManager& Timers = GetWorldTimerManager();
	Timers.ClearTimer(ComboTimer);

	State = EEnemyState::Attack;
	CurrentClubAttack = Attack;
	AttackStartTime = GetWorld()->GetTimeSeconds();
	CurrentAttackDuration = Sequence->GetPlayLength() / Rate;
	CurrentTrackTime = CurrentAttackDuration * Track;
	GetCharacterMovement()->bOrientRotationToMovement = false;
	GetCharacterMovement()->StopMovementImmediately();

	// the whole club (from just above the hands to the head) hits
	FMeleeHitShape Shape;
	Shape.Component = ClubRoot;
	Shape.Start = FVector(0.f, 0.f, 10.f);
	Shape.End = FVector(0.f, 0.f, ClubLength - ClubGripFromEnd);
	Shape.Radius = ClubHitRadius;
	const TArray<FMeleeHitShape> Shapes = { Shape };

	UMeleeHitComponent* Hit = FindComponentByClass<UMeleeHitComponent>();
	Hit->EndHitWindow();
	Timers.SetTimer(HitWindowStartTimer, FTimerDelegate::CreateWeakLambda(this, [this, Shapes, Damage]()
	{
		FindComponentByClass<UMeleeHitComponent>()->BeginHitWindow(Shapes, Damage);
	}), FMath::Max(CurrentAttackDuration * Window.X, 0.01f), false);
	Timers.SetTimer(HitWindowEndTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		FindComponentByClass<UMeleeHitComponent>()->EndHitWindow();
	}), FMath::Max(CurrentAttackDuration * Window.Y, 0.02f), false);
	Timers.SetTimer(AttackEndTimer, this, &AEnemyClub::EndAttack, FMath::Max(CurrentAttackDuration - BlendOut, 0.1f), false);

	// sweep -> backhand: starts from the sweep's follow-through pose
	if (Attack == EClubAttack::Sweep && bComboQueued)
	{
		bComboQueued = false;
		Timers.SetTimer(ComboTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
		{
			if (State == EEnemyState::Attack)
			{
				StartClubAttack(EClubAttack::SweepBack);
			}
		}), FMath::Max(CurrentAttackDuration * ComboChainFraction, 0.1f), false);
	}
}

void AEnemyClub::CancelAttack()
{
	Super::CancelAttack();
	GetWorldTimerManager().ClearTimer(ComboTimer);
	bComboQueued = false;
	CurrentClubAttack = EClubAttack::None;
}

void AEnemyClub::ResetEnemy()
{
	Super::ResetEnemy();

	GetCharacterMovement()->MaxWalkSpeed = ChaseSpeed;
	PlayHoldLoop();	// the reset stopped every montage
}
