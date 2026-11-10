// Temporary on-screen health / stamina bars (Slate, no assets needed). Replace with a UMG widget later.

#pragma once

#include "CoreMinimal.h"

class SWidget;
class UStatsComponent;

namespace PlayerStatsOverlay
{
	/** Top-left health (red) and stamina (green) bars that read their values from Stats every frame, plus a line of text below (potions). Bar length follows the max value */
	TSharedRef<SWidget> Create(UStatsComponent* Stats, TAttribute<FText> InfoText = TAttribute<FText>());
}
