// Souls-style boss health bar at the bottom of the screen (name + red bar), shared by every boss.

#pragma once

#include "CoreMinimal.h"
#include "Widgets/SWidget.h"

class UStatsComponent;
class UWorld;

namespace BossHealthBar
{
	/** Adds a bar for Stats to the viewport (does nothing if InOutWidget already holds one) */
	void Show(UWorld* World, TSharedPtr<SWidget>& InOutWidget, const FText& BossName, UStatsComponent* Stats);

	/** Removes the bar (safe to call when none is shown) */
	void Hide(UWorld* World, TSharedPtr<SWidget>& InOutWidget);
}
