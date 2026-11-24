// Save game: written ONLY when the player rests at a bonfire (AOss_TermProjectCharacter::SaveAtBonfire), read when the
// level starts (character BeginPlay: stats + spawn at the saved bonfire; UBossProgressSubsystem: defeated bosses).
// Console: DeleteSave -> next start is a new game.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "SoulsSaveGame.generated.h"

UCLASS()
class USoulsSaveGame : public USaveGame
{
	GENERATED_BODY()

public:

	static const FString SlotName;
	static constexpr int32 UserIndex = 0;

	/** Loads the save (null if there is none) */
	static USoulsSaveGame* Load();

	UPROPERTY()
	int32 Souls = 0;

	UPROPERTY()
	int32 VigorLevel = 1;

	UPROPERTY()
	int32 EnduranceLevel = 1;

	UPROPERTY()
	int32 StrengthLevel = 1;

	/** Bonfire rested at (actor name, stable for placed actors) and the spot in front of it */
	UPROPERTY()
	FName BonfireName;

	UPROPERTY()
	FTransform BonfireRespawn;

	/** "Fishman", "Wolf", "Tree" */
	UPROPERTY()
	TArray<FName> DefeatedBosses;

	/** Where Bonfire_Main is (travel target), if it was ever seen */
	UPROPERTY()
	bool bKnowsMainBonfire = false;

	UPROPERTY()
	FTransform MainBonfireRespawn;

	/** Player body mesh (changed by AModelSwapVolume); empty = the Blueprint's default */
	UPROPERTY()
	FSoftObjectPath BodyMesh;
};
