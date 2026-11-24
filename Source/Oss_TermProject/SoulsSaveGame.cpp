// Save game, see SoulsSaveGame.h

#include "SoulsSaveGame.h"
#include "Kismet/GameplayStatics.h"

const FString USoulsSaveGame::SlotName = TEXT("SoulsSave");

USoulsSaveGame* USoulsSaveGame::Load()
{
	if (!UGameplayStatics::DoesSaveGameExist(SlotName, UserIndex))
	{
		return nullptr;
	}
	return Cast<USoulsSaveGame>(UGameplayStatics::LoadGameFromSlot(SlotName, UserIndex));
}
