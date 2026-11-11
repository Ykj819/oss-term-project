// Temporary level-up menu (Slate, no assets needed). Opened by talking to the FireGirl. Replace with a UMG widget later.

#pragma once

#include "CoreMinimal.h"

class SWidget;
class AOss_TermProjectCharacter;

namespace LevelUpMenuWidget
{
	/** Centered panel: level, souls, cost, a [+] button per stat (spends souls on the character), and a close button */
	TSharedRef<SWidget> Create(AOss_TermProjectCharacter* Character);
}
