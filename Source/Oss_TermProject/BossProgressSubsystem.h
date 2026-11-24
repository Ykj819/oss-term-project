// Tracks which bosses are dead. Starts from the save game (USoulsSaveGame, written at bonfires) and adds the bosses
// killed this session. When all three (Fishman, Wolf, Tree) are defeated, the level actor tagged "DisableFence" (label
// DisableFence in Lvl_ThirdPerson, a StaticMeshActor) swings +90 degrees about its Y (pitch) axis over FenceSwingTime
// (instantly when the save already had all three) and the FireGirl vanishes. Bosses call NotifyBossDefeated from
// HandleDeath and destroy themselves in BeginPlay if IsBossDefeated. If the fence is streamed out (World Partition) it is
// looked for again every second until it is found. Game worlds only.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "BossProgressSubsystem.generated.h"

UCLASS()
class UBossProgressSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:

	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;

	/** Boss ids: "Fishman", "Wolf", "Tree" */
	void NotifyBossDefeated(FName BossId);

	bool IsBossDefeated(FName BossId) const { return DefeatedBosses.Contains(BossId); }

	bool AreAllBossesDefeated() const { return DefeatedBosses.Num() >= RequiredBosses; }

	TArray<FName> GetDefeatedBosses() const { return DefeatedBosses.Array(); }

	static constexpr int32 RequiredBosses = 3;
	static constexpr float FenceSwingTime = 2.f;
	static constexpr float FenceSwingDegrees = 90.f;

protected:

	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;

private:

	TSet<FName> DefeatedBosses;
	bool bFenceOpening = false;
	/** Loaded with all bosses dead: the fence is simply already open */
	bool bFenceInstant = false;

	TWeakObjectPtr<AActor> Fence;
	FQuat FenceStart;
	FQuat FenceEnd;
	float FenceAlpha = 0.f;
	FTimerHandle FenceTimer;

	void TryOpenFence();
	void StepFence();
	AActor* FindFence() const;
};
