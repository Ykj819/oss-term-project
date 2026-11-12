// Autumn tree boss: stationary, branch attacks in front, root spikes everywhere else, phase 2 leaf storm.

#include "TreeBoss.h"
#include "RootSpike.h"
#include "StatsComponent.h"
#include "BossHealthBar.h"
#include "MeleeHitComponent.h"
#include "Oss_TermProjectCharacter.h"
#include "Oss_TermProject.h"
#include "AIController.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/CapsuleComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
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
	TSoftObjectPtr<UAnimSequenceBase> TreeAnim(const TCHAR* Name)
	{
		return TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(FString::Printf(TEXT("/Game/Characters/Tree/Anims/%s.%s"), Name, Name)));
	}

	constexpr float CapsuleRadius = 135.f;
	constexpr float CapsuleHalfHeight = 330.f;

	// leaf storm volume around the player
	constexpr float StormRadius = 1800.f;
	constexpr float StormTop = 1000.f;
}

ATreeBoss::ATreeBoss()
{
	PrimaryActorTick.bCanEverTick = true;

	// the capsule covers the jar-shaped trunk (the canopy and branches are not hittable)
	GetCapsuleComponent()->InitCapsuleSize(CapsuleRadius, CapsuleHalfHeight);
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);

	// mesh: made in Blender facing -Y (like the mannequin) -> -90 yaw; origin at the roots
	static ConstructorHelpers::FObjectFinder<USkeletalMesh> TreeMesh(TEXT("/Game/Characters/Tree/SK_Tree.SK_Tree"));
	if (TreeMesh.Succeeded())
	{
		GetMesh()->SetSkeletalMeshAsset(TreeMesh.Object);
	}
	GetMesh()->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -CapsuleHalfHeight), FRotator(0.f, -90.f, 0.f));
	GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	// it never moves or turns
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	AIControllerClass = AAIController::StaticClass();
	bUseControllerRotationYaw = false;
	GetCharacterMovement()->bOrientRotationToMovement = false;
	GetCharacterMovement()->bUseControllerDesiredRotation = false;
	GetCharacterMovement()->MaxWalkSpeed = 0.f;

	Stats = CreateDefaultSubobject<UStatsComponent>(TEXT("Stats"));
	MeleeHit = CreateDefaultSubobject<UMeleeHitComponent>(TEXT("MeleeHit"));
	MeleeHit->IgnoreTags.Add(TEXT("Enemy"));

	// ---- phase 2 leaf storm
	StormPostProcess = CreateDefaultSubobject<UPostProcessComponent>(TEXT("StormPostProcess"));
	StormPostProcess->SetupAttachment(RootComponent);
	StormPostProcess->bUnbound = true;
	StormPostProcess->BlendWeight = 0.f;
	FPostProcessSettings& PP = StormPostProcess->Settings;
	PP.bOverride_VignetteIntensity = true;
	PP.VignetteIntensity = 1.3f;
	PP.bOverride_SceneColorTint = true;
	PP.SceneColorTint = FLinearColor(1.f, 0.8f, 0.62f);
	PP.bOverride_ColorSaturation = true;
	PP.ColorSaturation = FVector4(0.75f, 0.75f, 0.75f, 1.f);
	PP.bOverride_DepthOfFieldFocalDistance = true;
	PP.DepthOfFieldFocalDistance = 700.f;
	PP.bOverride_DepthOfFieldFstop = true;
	PP.DepthOfFieldFstop = 1.2f;
	PP.bOverride_DepthOfFieldMinFstop = true;
	PP.DepthOfFieldMinFstop = 1.2f;

	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(TEXT("/Engine/BasicShapes/Cube.Cube"));
	StormLeaves = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("StormLeaves"));
	StormLeaves->SetupAttachment(RootComponent);
	StormLeaves->SetUsingAbsoluteLocation(true);
	StormLeaves->SetUsingAbsoluteRotation(true);
	StormLeaves->SetUsingAbsoluteScale(true);
	StormLeaves->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	StormLeaves->SetGenerateOverlapEvents(false);
	StormLeaves->SetCastShadow(false);
	StormLeaves->SetCanEverAffectNavigation(false);
	if (CubeMesh.Succeeded())
	{
		StormLeaves->SetStaticMesh(CubeMesh.Object);
	}

	IdleAnim = TreeAnim(TEXT("Tree_Idle"));
	SlamRightAnim = TreeAnim(TEXT("Tree_Slam_R"));
	SlamLeftAnim = TreeAnim(TEXT("Tree_Slam_L"));
	SweepAnim = TreeAnim(TEXT("Tree_Sweep"));
	SummonAnim = TreeAnim(TEXT("Tree_Summon"));
	RoarAnim = TreeAnim(TEXT("Tree_Roar"));
	DeathAnim = TreeAnim(TEXT("Tree_Death"));

	Tags.Add(TEXT("LockOnTarget"));
	Tags.Add(TEXT("Enemy"));
}

void ATreeBoss::BeginPlay()
{
	Super::BeginPlay();

	if (UClass* Class = AnimClass.LoadSynchronous())
	{
		GetMesh()->SetAnimInstanceClass(Class);
	}
	else
	{
		UE_LOG(LogOss_TermProject, Warning, TEXT("'%s': anim blueprint %s not found - create ABP_Tree (Slot 'DefaultSlot' -> Output Pose)"), *GetNameSafe(this), *AnimClass.ToString());
		if (GEngine)
		{
			GEngine->AddOnScreenDebugMessage(-1, 10.f, FColor::Red, TEXT("TreeBoss: ABP_Tree missing (Content/Characters/Tree)"));
		}
	}

	for (TSoftObjectPtr<UAnimSequenceBase>* Anim : { &IdleAnim, &SlamRightAnim, &SlamLeftAnim, &SweepAnim, &SummonAnim, &RoarAnim, &DeathAnim })
	{
		if (!Anim->LoadSynchronous())
		{
			UE_LOG(LogOss_TermProject, Warning, TEXT("'%s': animation %s not found (import Export/Tree_*.fbx into /Game/Characters/Tree/Anims)"), *GetNameSafe(this), *Anim->ToString());
		}
	}

	StormLeaves->SetWorldTransform(FTransform::Identity);
	if (UMaterialInstanceDynamic* LeafMaterial = StormLeaves->CreateDynamicMaterialInstance(0))
	{
		LeafMaterial->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.75f, 0.2f, 0.03f));
	}

	Stats->SetMaxHealth(BossHealth);
	Stats->RestoreAll();
	Stats->OnDeath.AddDynamic(this, &ATreeBoss::HandleDeath);
	MeleeHit->bDebugDraw = bDebugHits;

	PlayIdle();
}

void ATreeBoss::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	ShowHealthBar(false);
	Super::EndPlay(EndPlayReason);
}

// ---------------------------------------------------------------- helpers

APawn* ATreeBoss::GetPlayer() const
{
	APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!Player || !Player->CanBeDamaged())
	{
		return nullptr;
	}
	if (const AOss_TermProjectCharacter* PlayerCharacter = Cast<AOss_TermProjectCharacter>(Player))
	{
		if ((PlayerCharacter->GetStats() && PlayerCharacter->GetStats()->IsDead()) || PlayerCharacter->IsResting())
		{
			return nullptr;
		}
	}
	return Player;
}

void ATreeBoss::GetPlayerOffset(const APawn* Player, float& OutDistance, float& OutYaw) const
{
	const FVector Local = GetActorTransform().InverseTransformPositionNoScale(Player->GetActorLocation());
	OutDistance = FVector2D(Local.X, Local.Y).Size();
	OutYaw = FMath::RadiansToDegrees(FMath::Atan2(Local.Y, Local.X));
}

float ATreeBoss::PlayAnim(const TSoftObjectPtr<UAnimSequenceBase>& Anim, float Rate, int32 Loops, float BlendIn, float BlendOut)
{
	UAnimSequenceBase* Sequence = Anim.Get();
	UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance();
	if (!Sequence || !AnimInstance || !AnimInstance->PlaySlotAnimationAsDynamicMontage(Sequence, SlotName, BlendIn, BlendOut, Rate, Loops))
	{
		return 0.f;
	}
	return Sequence->GetPlayLength() / FMath::Max(Rate, 0.05f);
}

void ATreeBoss::PlayIdle()
{
	if (CurrentLoop && CurrentLoop == IdleAnim.Get())
	{
		return;
	}
	CurrentLoop = IdleAnim.Get();
	PlayAnim(IdleAnim, 1.f, 100000, 0.3f, 0.3f);
}

// ---------------------------------------------------------------- AI

void ATreeBoss::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	UpdateStorm(DeltaSeconds);

	if (State == ETreeState::Dead || State == ETreeState::Action)
	{
		return;
	}

	APawn* Player = GetPlayer();

	if (State == ETreeState::Dormant)
	{
		if (Player)
		{
			float Distance, Yaw;
			GetPlayerOffset(Player, Distance, Yaw);
			FHitResult Hit;
			FCollisionQueryParams Params(SCENE_QUERY_STAT(TreeSight), false, this);
			const bool bVisible = !GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation(), Player->GetActorLocation(), ECC_Visibility, Params) || Hit.GetActor() == Player;
			if (Distance <= AggroRange && bVisible)
			{
				Engage();
			}
		}
		return;
	}

	// Idle: wait for the pause to end (and for a player to fight)
	if (Player && GetWorld()->GetTimeSeconds() >= StateEndTime)
	{
		Decide();
	}
}

void ATreeBoss::Engage()
{
	ShowHealthBar(true);
	NextSummonTime = GetWorld()->GetTimeSeconds() + 1.5f;
	EnterIdle(0.6f);
}

ETreeAction ATreeBoss::PickBranchAttack(float PlayerYaw)
{
	// the sweep starts at its right and ends in front-left; the slams land at the front-right / front-left
	ETreeAction Pick;
	if (PlayerYaw > 30.f)
	{
		Pick = FMath::FRand() < 0.7f ? ETreeAction::SlamRight : ETreeAction::Sweep;
	}
	else if (PlayerYaw < -30.f)
	{
		Pick = ETreeAction::SlamLeft;
	}
	else
	{
		const float Roll = FMath::FRand();
		Pick = Roll < 0.55f ? ETreeAction::Sweep : (PlayerYaw >= 0.f ? ETreeAction::SlamRight : ETreeAction::SlamLeft);
	}

	// no third repeat in a row
	if (Pick == LastAttack && SameAttackCount >= 2)
	{
		if (Pick == ETreeAction::Sweep)
		{
			Pick = PlayerYaw >= 0.f ? ETreeAction::SlamRight : ETreeAction::SlamLeft;
		}
		else if (PlayerYaw > -30.f)
		{
			Pick = ETreeAction::Sweep;
		}
		else if (GetWorld()->GetTimeSeconds() >= NextSummonTime)
		{
			Pick = ETreeAction::Summon;
		}
	}
	return Pick;
}

void ATreeBoss::Decide()
{
	if (State == ETreeState::Dead)
	{
		return;
	}

	// phase 2 starts with a roar (the storm rises during it)
	if (bPhaseTwo && !bStorm)
	{
		StartAction(ETreeAction::Roar);
		return;
	}

	APawn* Player = GetPlayer();
	if (!Player)
	{
		EnterIdle(0.5f);
		return;
	}

	float Distance, Yaw;
	GetPlayerOffset(Player, Distance, Yaw);
	const float Now = GetWorld()->GetTimeSeconds();
	const bool bCanSummon = Now >= NextSummonTime;
	const bool bInReach = Distance <= ArmRange && FMath::Abs(Yaw) <= FrontAngle;

	if (bInReach && !(bCanSummon && FMath::FRand() < 0.15f))
	{
		StartAction(PickBranchAttack(Yaw));
	}
	else if (bCanSummon)
	{
		StartAction(ETreeAction::Summon);
	}
	else
	{
		// out of reach (behind it / far away) and the roots aren't ready: wait
		EnterIdle(0.3f);
	}
}

void ATreeBoss::StartAction(ETreeAction Action)
{
	const TSoftObjectPtr<UAnimSequenceBase>* Anim = nullptr;
	switch (Action)
	{
	case ETreeAction::SlamRight:	Anim = &SlamRightAnim; break;
	case ETreeAction::SlamLeft:		Anim = &SlamLeftAnim; break;
	case ETreeAction::Sweep:		Anim = &SweepAnim; break;
	case ETreeAction::Summon:		Anim = &SummonAnim; break;
	case ETreeAction::Roar:			Anim = &RoarAnim; break;
	default:						break;
	}

	CurrentLoop = nullptr;
	const float Length = Anim ? PlayAnim(*Anim, PlayRate(), 1, 0.2f, 0.3f) : 0.f;
	if (Length <= 0.f)
	{
		if (Action == ETreeAction::Roar)
		{
			SetStorm(true);	// no roar animation: still start the storm so this isn't retried forever
		}
		EnterIdle(1.f);
		return;
	}

	State = ETreeState::Action;
	CurrentAction = Action;
	FTimerManager& Timers = GetWorldTimerManager();

	if (Action == ETreeAction::Roar)
	{
		Timers.SetTimer(StormStartTimer, FTimerDelegate::CreateWeakLambda(this, [this]() { SetStorm(true); }), Length * 0.35f, false);
		if (GEngine)
		{
			GEngine->AddOnScreenDebugMessage(-1, 3.f, FColor(255, 120, 40), FString::Printf(TEXT("%s calls the autumn storm"), *BossName.ToString()), true, FVector2D(2.f, 2.f));
		}
	}
	else if (Action == ETreeAction::Summon)
	{
		NextSummonTime = GetWorld()->GetTimeSeconds() + SummonCooldown * (bPhaseTwo ? 0.7f : 1.f);
		SpikesLeft = bPhaseTwo ? SpikeCount.Y : SpikeCount.X;
		Timers.SetTimer(SpikeTimer, this, &ATreeBoss::SpawnNextSpike, FMath::Max(Length * FirstSpikeFraction, 0.05f), false);
	}
	else
	{
		SameAttackCount = (Action == LastAttack) ? SameAttackCount + 1 : 1;
		LastAttack = Action;
		ScheduleHitWindow(Action, Length);
	}

	Timers.SetTimer(ActionEndTimer, this, &ATreeBoss::EndAction, FMath::Max(Length - 0.25f, 0.1f), false);
}

void ATreeBoss::ScheduleHitWindow(ETreeAction Action, float AnimLength)
{
	FTimerManager& Timers = GetWorldTimerManager();
	Timers.ClearTimer(HitStartTimer);
	Timers.ClearTimer(HitEndTimer);
	MeleeHit->EndHitWindow();

	// bone segments run along the bone (+Y, as exported from Blender); lengths in cm
	auto Segment = [this](const TCHAR* Bone, float Length, float Radius)
	{
		FMeleeHitShape S;
		S.Component = GetMesh();
		S.Socket = Bone;
		S.Start = FVector::ZeroVector;
		S.End = FVector(0.f, Length, 0.f);
		S.Radius = Radius;
		return S;
	};
	auto Sphere = [this](const TCHAR* Bone, const FVector& Offset, float Radius)
	{
		FMeleeHitShape S;
		S.Component = GetMesh();
		S.Socket = Bone;
		S.Start = Offset;
		S.End = Offset;
		S.Radius = Radius;
		return S;
	};

	TArray<FMeleeHitShape> Shapes;
	FVector2D Window;
	float Damage = 0.f;
	switch (Action)
	{
	case ETreeAction::SlamRight:
	case ETreeAction::SlamLeft:
	{
		const bool bRight = Action == ETreeAction::SlamRight;
		Shapes.Add(Segment(bRight ? TEXT("branch_r_02") : TEXT("branch_l_02"), 140.f, 45.f));
		Shapes.Add(Segment(bRight ? TEXT("branch_r_03") : TEXT("branch_l_03"), 110.f, 55.f));
		// impact around the claws
		Shapes.Add(Sphere(bRight ? TEXT("branch_r_03") : TEXT("branch_l_03"), FVector(0.f, 100.f, 0.f), 130.f));
		Window = SlamHitWindow;
		Damage = SlamDamage;
		break;
	}
	case ETreeAction::Sweep:
		Shapes.Add(Segment(TEXT("branch_r_02"), 140.f, 50.f));
		Shapes.Add(Segment(TEXT("branch_r_03"), 115.f, 60.f));
		Window = SweepHitWindow;
		Damage = SweepDamage;
		break;
	default:
		return;
	}

	MeleeHit->bDebugDraw = bDebugHits;
	Timers.SetTimer(HitStartTimer, FTimerDelegate::CreateWeakLambda(this, [this, Shapes, Damage]()
	{
		MeleeHit->BeginHitWindow(Shapes, Damage);
	}), FMath::Max(AnimLength * Window.X, 0.01f), false);
	Timers.SetTimer(HitEndTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		MeleeHit->EndHitWindow();
	}), FMath::Max(AnimLength * Window.Y, 0.02f), false);
}

void ATreeBoss::SpawnNextSpike()
{
	APawn* Player = GetPlayer();
	if (!Player || State == ETreeState::Dead || SpikesLeft <= 0)
	{
		return;
	}

	// slightly ahead of where the player is going, on the ground under them
	const FVector Aim = Player->GetActorLocation() + Player->GetVelocity() * FVector(0.3f, 0.3f, 0.f);
	FVector Ground = Aim - FVector(0.f, 0.f, 90.f);
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(RootSpikeGround), false, this);
	Params.AddIgnoredActor(Player);
	if (GetWorld()->LineTraceSingleByChannel(Hit, Aim + FVector(0.f, 0.f, 100.f), Aim - FVector(0.f, 0.f, 600.f), ECC_Visibility, Params))
	{
		Ground = Hit.ImpactPoint;
	}

	ActiveSpikes.RemoveAll([](const TWeakObjectPtr<ARootSpike>& S) { return !S.IsValid(); });
	const FTransform SpawnTransform(FRotator(0.f, FMath::FRandRange(0.f, 360.f), 0.f), Ground);
	if (ARootSpike* Spike = GetWorld()->SpawnActorDeferred<ARootSpike>(ARootSpike::StaticClass(), SpawnTransform, this, this, ESpawnActorCollisionHandlingMethod::AlwaysSpawn))
	{
		Spike->Damage = SpikeDamage;
		Spike->WarnTime = bPhaseTwo ? 0.85f : 1.1f;
		Spike->FinishSpawning(SpawnTransform);
		ActiveSpikes.Add(Spike);
	}

	if (--SpikesLeft > 0)
	{
		GetWorldTimerManager().SetTimer(SpikeTimer, this, &ATreeBoss::SpawnNextSpike, bPhaseTwo ? SpikeInterval.Y : SpikeInterval.X, false);
	}
}

void ATreeBoss::EndAction()
{
	FTimerManager& Timers = GetWorldTimerManager();
	Timers.ClearTimer(HitStartTimer);
	Timers.ClearTimer(HitEndTimer);
	MeleeHit->EndHitWindow();

	const ETreeAction Finished = CurrentAction;
	CurrentAction = ETreeAction::None;

	// a roar or summon flows straight into the next decision; attacks leave an opening
	const float Scale = bPhaseTwo ? PhaseTwoRecoverScale : 1.f;
	const float Pause = (Finished == ETreeAction::Roar || Finished == ETreeAction::Summon)
		? 0.4f
		: FMath::FRandRange(RecoverTime.X, FMath::Max(RecoverTime.X, RecoverTime.Y)) * Scale;
	EnterIdle(Pause);
}

void ATreeBoss::EnterIdle(float Duration)
{
	State = ETreeState::Idle;
	CurrentAction = ETreeAction::None;
	StateEndTime = GetWorld()->GetTimeSeconds() + Duration;
	PlayIdle();
}

void ATreeBoss::ClearActionTimers()
{
	FTimerManager& Timers = GetWorldTimerManager();
	Timers.ClearTimer(ActionEndTimer);
	Timers.ClearTimer(HitStartTimer);
	Timers.ClearTimer(HitEndTimer);
	Timers.ClearTimer(SpikeTimer);
	Timers.ClearTimer(StormStartTimer);
	MeleeHit->EndHitWindow();
	SpikesLeft = 0;
}

// ---------------------------------------------------------------- leaf storm

void ATreeBoss::SetStorm(bool bOn)
{
	if (bStorm == bOn)
	{
		return;
	}
	bStorm = bOn;

	if (bOn)
	{
		const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
		const FVector Center = Player ? Player->GetActorLocation() : GetActorLocation();
		Leaves.SetNum(StormLeafCount);
		StormLeaves->ClearInstances();
		TArray<FTransform> Transforms;
		Transforms.Reserve(Leaves.Num());
		for (FLeaf& Leaf : Leaves)
		{
			RespawnLeaf(Leaf, Center, true);
			Transforms.Add(FTransform(Leaf.Position));
		}
		StormLeaves->AddInstances(Transforms, false, true);
		StormLeaves->SetVisibility(true);
	}
}

void ATreeBoss::RespawnLeaf(FLeaf& Leaf, const FVector& Center, bool bAnywhere)
{
	const FVector2D Disc = FMath::RandPointInCircle(StormRadius);
	const float Height = bAnywhere ? FMath::FRandRange(-80.f, StormTop) : FMath::FRandRange(StormTop * 0.6f, StormTop);
	Leaf.Position = Center + FVector(Disc.X, Disc.Y, Height);
	Leaf.Velocity = FVector::ZeroVector;
	Leaf.SpinAxis = FMath::VRand();
	Leaf.Spin = FMath::FRandRange(0.f, 2.f * PI);
	Leaf.SpinSpeed = FMath::FRandRange(2.f, 7.f);
}

void ATreeBoss::UpdateStorm(float DeltaSeconds)
{
	// view effect fades in / out
	const float Target = bStorm ? 1.f : 0.f;
	StormWeight = FMath::FInterpConstantTo(StormWeight, Target, DeltaSeconds, 0.5f);
	StormPostProcess->BlendWeight = StormWeight * StormIntensity;

	if (StormWeight <= 0.f && !bStorm)
	{
		if (Leaves.Num() > 0)
		{
			Leaves.Reset();
			StormLeaves->ClearInstances();
		}
		return;
	}
	if (Leaves.Num() == 0)
	{
		return;
	}

	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	const FVector Center = Player ? Player->GetActorLocation() : GetActorLocation();
	const FVector Eye = GetActorLocation();
	const float Time = GetWorld()->GetTimeSeconds();
	// leaves fade in / out by shrinking with the storm
	const float Size = FMath::Clamp(StormWeight * 1.5f, 0.f, 1.f);

	TArray<FTransform> Transforms;
	Transforms.SetNum(Leaves.Num());
	for (int32 i = 0; i < Leaves.Num(); ++i)
	{
		FLeaf& Leaf = Leaves[i];

		// swirl around the tree, gusting, drifting down
		FVector FromTree = Leaf.Position - Eye;
		FromTree.Z = 0.f;
		const FVector Tangent = FVector::CrossProduct(FVector::UpVector, FromTree.GetSafeNormal());
		const float Gust = 0.6f + 0.4f * FMath::Sin(Time * 1.3f + i * 0.37f);
		const FVector Wind = Tangent * 650.f * Gust - FromTree.GetSafeNormal() * 60.f
			+ FVector(FMath::Sin(Time * 2.1f + i), FMath::Cos(Time * 1.7f + i * 1.3f), 0.f) * 120.f
			+ FVector(0.f, 0.f, -140.f + 60.f * FMath::Sin(Time * 3.f + i * 0.71f));
		Leaf.Velocity = FMath::VInterpTo(Leaf.Velocity, Wind, DeltaSeconds, 2.f);
		Leaf.Position += Leaf.Velocity * DeltaSeconds;
		Leaf.Spin += Leaf.SpinSpeed * DeltaSeconds;

		const FVector Offset = Leaf.Position - Center;
		if (FVector2D(Offset.X, Offset.Y).SizeSquared() > FMath::Square(StormRadius) || Offset.Z < -150.f || Offset.Z > StormTop + 200.f)
		{
			RespawnLeaf(Leaf, Center, false);
		}

		Transforms[i] = FTransform(FQuat(Leaf.SpinAxis, Leaf.Spin), Leaf.Position, FVector(0.26f, 0.18f, 0.008f) * Size);
	}
	StormLeaves->BatchUpdateInstancesTransforms(0, Transforms, true, true, true);
}

// ---------------------------------------------------------------- damage / death / reset

float ATreeBoss::TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator, AActor* DamageCauser)
{
	const float Damage = Super::TakeDamage(DamageAmount, DamageEvent, EventInstigator, DamageCauser);
	if (Damage <= 0.f || State == ETreeState::Dead)
	{
		return 0.f;
	}

	if (State == ETreeState::Dormant)
	{
		Engage();
	}

	const float Taken = Stats->ApplyDamage(Damage, DamageCauser);

	if (!bPhaseTwo && !Stats->IsDead() && Stats->GetHealth() <= Stats->GetMaxHealth() * PhaseTwoHealth)
	{
		bPhaseTwo = true;
		if (State == ETreeState::Idle)
		{
			Decide();	// roar right away
		}
	}
	return Taken;
}

void ATreeBoss::HandleDeath(AActor* DamageCauser)
{
	State = ETreeState::Dead;
	CurrentAction = ETreeAction::None;
	CurrentLoop = nullptr;
	ClearActionTimers();
	SetStorm(false);

	// withers and stays that way (the montage holds its last frame)
	if (UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance())
	{
		AnimInstance->StopAllMontages(0.2f);
		if (UAnimSequenceBase* Death = DeathAnim.Get())
		{
			if (UAnimMontage* Montage = AnimInstance->PlaySlotAnimationAsDynamicMontage(Death, SlotName, 0.2f, 0.f, 1.f, 1))
			{
				Montage->bEnableAutoBlendOut = false;
			}
		}
	}

	if (AOss_TermProjectCharacter* Player = Cast<AOss_TermProjectCharacter>(UGameplayStatics::GetPlayerPawn(this, 0)))
	{
		Player->AddSouls(SoulReward);
	}

	ShowHealthBar(false);
	Tags.Remove(TEXT("LockOnTarget"));

	if (GEngine)
	{
		GEngine->AddOnScreenDebugMessage(-1, 5.f, FColor(255, 210, 90), TEXT("GREAT ENEMY FELLED"), true, FVector2D(3.f, 3.f));
	}
	UE_LOG(LogOss_TermProject, Log, TEXT("'%s' defeated"), *GetNameSafe(this));
}

void ATreeBoss::ResetBoss()
{
	if (State == ETreeState::Dead)
	{
		return;
	}

	ClearActionTimers();
	for (const TWeakObjectPtr<ARootSpike>& Spike : ActiveSpikes)
	{
		if (Spike.IsValid())
		{
			Spike->Destroy();
		}
	}
	ActiveSpikes.Reset();

	if (UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance())
	{
		AnimInstance->StopAllMontages(0.f);
	}
	CurrentLoop = nullptr;

	Stats->RestoreAll();
	bPhaseTwo = false;
	SetStorm(false);
	CurrentAction = ETreeAction::None;
	LastAttack = ETreeAction::None;
	SameAttackCount = 0;
	State = ETreeState::Dormant;
	ShowHealthBar(false);
	PlayIdle();
}

void ATreeBoss::ShowHealthBar(bool bShow)
{
	if (bShow)
	{
		BossHealthBar::Show(GetWorld(), HealthBar, BossName, Stats);
	}
	else
	{
		BossHealthBar::Hide(GetWorld(), HealthBar);
	}
}
