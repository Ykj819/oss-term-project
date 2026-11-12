// Souls-style boss health bar at the bottom of the screen.

#include "BossHealthBar.h"
#include "StatsComponent.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Styling/CoreStyle.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"

void BossHealthBar::Show(UWorld* World, TSharedPtr<SWidget>& InOutWidget, const FText& BossName, UStatsComponent* Stats)
{
	UGameViewportClient* Viewport = World ? World->GetGameViewport() : nullptr;
	if (InOutWidget.IsValid() || !Viewport)
	{
		return;
	}

	TWeakObjectPtr<UStatsComponent> WeakStats(Stats);
	const FSlateBrush* White = FCoreStyle::Get().GetBrush("WhiteBrush");
	constexpr float BarWidth = 900.f;

	InOutWidget = SNew(SBox)
		.HAlign(HAlign_Center)
		.VAlign(VAlign_Bottom)
		.Padding(FMargin(0.f, 0.f, 0.f, 110.f))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
			[
				SNew(STextBlock)
				.Text(BossName)
				.Font(FCoreStyle::GetDefaultFontStyle("Bold", 18))
				.ColorAndOpacity(FLinearColor(0.95f, 0.9f, 0.75f))
				.ShadowOffset(FVector2D(1.f, 1.f))
			]
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(SBox).WidthOverride(BarWidth + 4.f).HeightOverride(16.f)
				[
					SNew(SOverlay)
					+ SOverlay::Slot()
					[
						SNew(SImage).Image(White).ColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, 0.75f))
					]
					+ SOverlay::Slot().HAlign(HAlign_Left).Padding(2.f)
					[
						SNew(SBox)
						.WidthOverride_Lambda([WeakStats, BarWidth]()
						{
							const UStatsComponent* S = WeakStats.Get();
							return FOptionalSize(S ? BarWidth * FMath::Clamp(S->GetHealth() / S->GetMaxHealth(), 0.f, 1.f) : 0.f);
						})
						[
							SNew(SImage).Image(White).ColorAndOpacity(FLinearColor(0.6f, 0.04f, 0.04f))
						]
					]
				]
			]
		];

	Viewport->AddViewportWidgetContent(InOutWidget.ToSharedRef(), 9);
}

void BossHealthBar::Hide(UWorld* World, TSharedPtr<SWidget>& InOutWidget)
{
	UGameViewportClient* Viewport = World ? World->GetGameViewport() : nullptr;
	if (InOutWidget.IsValid() && Viewport)
	{
		Viewport->RemoveViewportWidgetContent(InOutWidget.ToSharedRef());
	}
	InOutWidget.Reset();
}
