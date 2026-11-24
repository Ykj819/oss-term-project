// Temporary title screen (Slate, no assets needed), shown by the player character when the level starts (game paused):
// Continue (only with a save: the save was already applied in BeginPlay, so it just closes), New Game (deletes the save
// and reloads the level, which then skips the title once), Quit. Replace with a proper menu map / UMG widget later.

#pragma once

#include "CoreMinimal.h"

class SWidget;
class AOss_TermProjectCharacter;

namespace TitleScreenWidget
{
	TSharedRef<SWidget> Create(AOss_TermProjectCharacter* Character, bool bHasSave);
}
