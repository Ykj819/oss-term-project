// Temporary level-up menu (Slate, no assets needed). Opened by talking to the FireGirl. Replace with a UMG widget later.

#include "LevelUpMenuWidget.h"
#include "Oss_TermProjectCharacter.h"
#include "StatsComponent.h"
#include "Styling/CoreStyle.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
	using FWeakChar = TWeakObjectPtr<AOss_TermProjectCharacter>;

	const FLinearColor TextColor(0.95f, 0.9f, 0.75f);
	const FLinearColor DimColor(0.6f, 0.58f, 0.5f);

	TSharedRef<STextBlock> MakeText(TAttribute<FText> Text, int32 Size, const FLinearColor& Color = TextColor)
	{
		return SNew(STextBlock)
			.Text(Text)
			.Font(FCoreStyle::GetDefaultFontStyle("Bold", Size))
			.ColorAndOpacity(Color)
			.ShadowOffset(FVector2D(1.f, 1.f));
	}

	/** "Vigor   3   Max HP 120   [+]" */
	TSharedRef<SWidget> MakeStatRow(FWeakChar WeakChar, ELevelStat Stat, const FString& Name)
	{
		auto LevelText = [WeakChar, Stat]()
		{
			return WeakChar.IsValid() ? FText::AsNumber(WeakChar->GetStatLevel(Stat)) : FText::GetEmpty();
		};
		auto EffectText = [WeakChar, Stat]()
		{
			const AOss_TermProjectCharacter* Char = WeakChar.Get();
			if (!Char || !Char->GetStats())
			{
				return FText::GetEmpty();
			}
			switch (Stat)
			{
			case ELevelStat::Vigor:		return FText::FromString(FString::Printf(TEXT("Max HP %d"), FMath::RoundToInt(Char->GetStats()->GetMaxHealth())));
			case ELevelStat::Endurance:	return FText::FromString(FString::Printf(TEXT("Max Stamina %d"), FMath::RoundToInt(Char->GetStats()->GetMaxStamina())));
			case ELevelStat::Strength:	return FText::FromString(FString::Printf(TEXT("Damage x%.1f"), Char->GetDamageMultiplier()));
			default:					return FText::GetEmpty();
			}
		};

		return SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
			[
				MakeText(FText::FromString(Name), 18)
			]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(16.f, 0.f)
			[
				SNew(SBox).WidthOverride(40.f)
				[
					MakeText(TAttribute<FText>::CreateLambda(LevelText), 18)
				]
			]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				SNew(SBox).WidthOverride(180.f)
				[
					MakeText(TAttribute<FText>::CreateLambda(EffectText), 14, DimColor)
				]
			]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				SNew(SButton)
				.IsEnabled_Lambda([WeakChar]() { return WeakChar.IsValid() && WeakChar->GetSouls() >= WeakChar->GetLevelUpCost(); })
				.OnClicked_Lambda([WeakChar, Stat]()
				{
					if (WeakChar.IsValid())
					{
						WeakChar->LevelUp(Stat);
					}
					return FReply::Handled();
				})
				.ContentPadding(FMargin(14.f, 2.f))
				[
					MakeText(FText::FromString(TEXT("+")), 18, FLinearColor::Black)
				]
			];
	}
}

TSharedRef<SWidget> LevelUpMenuWidget::Create(AOss_TermProjectCharacter* Character)
{
	FWeakChar WeakChar(Character);
	const FSlateBrush* White = FCoreStyle::Get().GetBrush("WhiteBrush");

	// "<Label><number>" read live from the character
	auto Line = [WeakChar](auto Getter, const FString& Label)
	{
		return TAttribute<FText>::CreateLambda([WeakChar, Getter, Label]()
		{
			return WeakChar.IsValid() ? FText::FromString(Label + FString::FromInt(Getter(WeakChar.Get()))) : FText::GetEmpty();
		});
	};

	return SNew(SBox)
		.HAlign(HAlign_Center)
		.VAlign(VAlign_Center)
		[
			SNew(SBox)
			.WidthOverride(520.f)
			[
				SNew(SOverlay)
				+ SOverlay::Slot()
				[
					SNew(SImage).Image(White).ColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, 0.8f))
				]
				+ SOverlay::Slot()
				.Padding(28.f)
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.f, 0.f, 0.f, 16.f)
					[
						MakeText(FText::FromString(TEXT("Level Up")), 26)
					]
					+ SVerticalBox::Slot().AutoHeight()
					[
						MakeText(Line([](AOss_TermProjectCharacter* C) { return C->GetPlayerLevel(); }, TEXT("Level  ")), 16)
					]
					+ SVerticalBox::Slot().AutoHeight()
					[
						MakeText(Line([](AOss_TermProjectCharacter* C) { return C->GetSouls(); }, TEXT("Souls  ")), 16)
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 16.f)
					[
						MakeText(Line([](AOss_TermProjectCharacter* C) { return C->GetLevelUpCost(); }, TEXT("Cost  ")), 16)
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f)
					[
						MakeStatRow(WeakChar, ELevelStat::Vigor, TEXT("Vigor"))
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f)
					[
						MakeStatRow(WeakChar, ELevelStat::Endurance, TEXT("Endurance"))
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f)
					[
						MakeStatRow(WeakChar, ELevelStat::Strength, TEXT("Strength"))
					]
					+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.f, 20.f, 0.f, 0.f)
					[
						SNew(SButton)
						.OnClicked_Lambda([WeakChar]()
						{
							if (WeakChar.IsValid())
							{
								WeakChar->CloseLevelUpMenu();
							}
							return FReply::Handled();
						})
						.ContentPadding(FMargin(24.f, 4.f))
						[
							MakeText(FText::FromString(TEXT("Close  [E]")), 14, FLinearColor::Black)
						]
					]
				]
			]
		];
}
