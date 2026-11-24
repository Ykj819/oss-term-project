// Opens the DisableFence when all bosses are dead, see BossProgressSubsystem.h

#include "BossProgressSubsystem.h"
#include "FireGirl.h"
#include "SoulsSaveGame.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "TimerManager.h"
#include "Components/SceneComponent.h"

namespace
{
	const FName FenceName(TEXT("DisableFence"));
	constexpr float FenceStep = 1.f / 60.f;
}

bool UBossProgressSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UBossProgressSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);

	// before any actor's BeginPlay: bosses already beaten in the save don't come back
	if (const USoulsSaveGame* Save = USoulsSaveGame::Load())
	{
		DefeatedBosses.Append(Save->DefeatedBosses);
	}
}

void UBossProgressSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);

	if (AreAllBossesDefeated())
	{
		bFenceOpening = true;
		bFenceInstant = true;
		TryOpenFence();
	}
}

void UBossProgressSubsystem::NotifyBossDefeated(FName BossId)
{
	DefeatedBosses.Add(BossId);
	UE_LOG(LogTemp, Log, TEXT("Boss defeated: %s (%d / %d)"), *BossId.ToString(), DefeatedBosses.Num(), RequiredBosses);
	if (AreAllBossesDefeated() && !bFenceOpening)
	{
		bFenceOpening = true;
		TryOpenFence();

		// the FireGirl leaves (ones streamed out destroy themselves in BeginPlay)
		for (TActorIterator<AFireGirl> It(GetWorld()); It; ++It)
		{
			It->Vanish();
		}
	}
}

AActor* UBossProgressSubsystem::FindFence() const
{
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		if (It->ActorHasTag(FenceName))
		{
			return *It;
		}
#if WITH_EDITOR
		if (It->GetActorLabel() == FenceName.ToString())
		{
			return *It;
		}
#endif
	}
	return nullptr;
}

void UBossProgressSubsystem::TryOpenFence()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	AActor* Found = FindFence();
	if (!Found)
	{
		// streamed out right now: look again later
		World->GetTimerManager().SetTimer(FenceTimer, this, &UBossProgressSubsystem::TryOpenFence, 1.f, false);
		return;
	}

	Fence = Found;
	if (USceneComponent* Root = Found->GetRootComponent())
	{
		Root->SetMobility(EComponentMobility::Movable);
	}
	const FRotator Start = Found->GetActorRotation();
	FenceStart = Start.Quaternion();
	// +90 on the Details panel's Y (pitch) value
	FenceEnd = FRotator(Start.Pitch + FenceSwingDegrees, Start.Yaw, Start.Roll).Quaternion();
	FenceAlpha = 0.f;
	if (bFenceInstant)
	{
		Found->SetActorRotation(FenceEnd);
		// World Partition reloads it closed after it streams out: keep an eye on it
		World->GetTimerManager().SetTimer(FenceTimer, [this]()
		{
			if (!Fence.IsValid())
			{
				TryOpenFence();
			}
		}, 1.f, true);
		return;
	}
	World->GetTimerManager().SetTimer(FenceTimer, this, &UBossProgressSubsystem::StepFence, FenceStep, true);
}

void UBossProgressSubsystem::StepFence()
{
	AActor* F = Fence.Get();
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	if (!F)
	{
		// streamed out mid-swing: it will simply be open when it comes back
		bFenceInstant = true;
		TryOpenFence();
		return;
	}
	FenceAlpha = FMath::Min(FenceAlpha + FenceStep / FenceSwingTime, 1.f);
	const float Eased = FMath::InterpEaseInOut(0.f, 1.f, FenceAlpha, 2.f);
	F->SetActorRotation(FQuat::Slerp(FenceStart, FenceEnd, Eased));
	if (FenceAlpha >= 1.f)
	{
		// done; from now on re-open it instantly whenever World Partition reloads it
		bFenceInstant = true;
		World->GetTimerManager().SetTimer(FenceTimer, [this]()
		{
			if (!Fence.IsValid())
			{
				TryOpenFence();
			}
		}, 1.f, true);
	}
}
