// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "Oss_TermProjectGameMode.generated.h"

/**
 *  Simple GameMode for a third person game
 */
UCLASS(abstract)
class AOss_TermProjectGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	
	/** Constructor */
	AOss_TermProjectGameMode();
};



