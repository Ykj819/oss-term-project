// Temporary on-screen health / stamina bars (Slate, no assets needed). Replace with a UMG widget later.

#include "PlayerStatsOverlay.h"
#include "StatsComponent.h"
#include "Styling/CoreStyle.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
	/** Pixels of bar per point of max value (100 -> 300px) */
	constexpr float PixelsPerPoint = 3.f;
	constexpr float Border = 2.f;

	TSharedRef<SWidget> MakeBar(TWeakObjectPtr<UStatsComponent> WeakStats, bool bHealth, const FLinearColor& Color, float Height)
	{
		const FSlateBrush* White = FCoreStyle::Get().GetBrush("WhiteBrush");

		auto GetMax = [WeakStats, bHealth]() -> float
		{
			const UStatsComponent* Stats = WeakStats.Get();
			return Stats ? (bHealth ? Stats->GetMaxHealth() : Stats->GetMaxStamina()) : 100.f;
		};
		auto GetValue = [WeakStats, bHealth]() -> float
		{
			const UStatsComponent* Stats = WeakStats.Get();
			return Stats ? (bHealth ? Stats->GetHealth() : Stats->GetStamina()) : 0.f;
		};

		return SNew(SBox)
			.WidthOverride_Lambda([GetMax]() { return FOptionalSize(GetMax() * PixelsPerPoint + Border * 2.f); })
			.HeightOverride(Height + Border * 2.f)
			[
				SNew(SOverlay)
				// frame
				+ SOverlay::Slot()
				[
					SNew(SImage).Image(White).ColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, 0.7f))
				]
				// fill
				+ SOverlay::Slot()
				.HAlign(HAlign_Left)
				.Padding(Border)
				[
					SNew(SBox)
					.WidthOverride_Lambda([GetValue]() { return FOptionalSize(GetValue() * PixelsPerPoint); })
					[
						SNew(SImage).Image(White).ColorAndOpacity(Color)
					]
				]
			];
	}
}

TSharedRef<SWidget> PlayerStatsOverlay::Create(UStatsComponent* Stats, TAttribute<FText> InfoText)
{
	TWeakObjectPtr<UStatsComponent> WeakStats(Stats);

	return SNew(SBox)
		.HAlign(HAlign_Left)
		.VAlign(VAlign_Top)
		.Padding(FMargin(40.f, 40.f))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.f, 0.f, 0.f, 6.f)
			[
				MakeBar(WeakStats, true, FLinearColor(0.75f, 0.05f, 0.05f), 14.f)
			]
			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				MakeBar(WeakStats, false, FLinearColor(0.1f, 0.65f, 0.15f), 10.f)
			]
			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.f, 8.f, 0.f, 0.f)
			[
				SNew(STextBlock)
				.Text(InfoText)
				.Font(FCoreStyle::GetDefaultFontStyle("Bold", 14))
				.ColorAndOpacity(FLinearColor::White)
				.ShadowOffset(FVector2D(1.f, 1.f))
			]
		];
}
