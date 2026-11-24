// Temporary title screen, see TitleScreenWidget.h

#include "TitleScreenWidget.h"
#include "Oss_TermProjectCharacter.h"
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

	TSharedRef<STextBlock> MakeText(const FString& Text, int32 Size, const FLinearColor& Color)
	{
		return SNew(STextBlock)
			.Text(FText::FromString(Text))
			.Font(FCoreStyle::GetDefaultFontStyle("Bold", Size))
			.ColorAndOpacity(Color)
			.ShadowOffset(FVector2D(2.f, 2.f));
	}

	TSharedRef<SWidget> MakeButton(const FString& Label, bool bEnabled, TFunction<void()> OnClick)
	{
		return SNew(SBox)
			.WidthOverride(320.f)
			.HeightOverride(56.f)
			[
				SNew(SButton)
				.IsEnabled(bEnabled)
				.HAlign(HAlign_Center)
				.VAlign(VAlign_Center)
				.OnClicked_Lambda([OnClick]()
				{
					OnClick();
					return FReply::Handled();
				})
				[
					MakeText(Label, 20, bEnabled ? FLinearColor::Black : FLinearColor(0.35f, 0.35f, 0.35f))
				]
			];
	}
}

TSharedRef<SWidget> TitleScreenWidget::Create(AOss_TermProjectCharacter* Character, bool bHasSave)
{
	FWeakChar WeakChar(Character);
	const FSlateBrush* White = FCoreStyle::Get().GetBrush("WhiteBrush");

	return SNew(SOverlay)
		// darkened game view behind the menu
		+ SOverlay::Slot()
		[
			SNew(SImage).Image(White).ColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, 0.72f))
		]
		+ SOverlay::Slot()
		.HAlign(HAlign_Center)
		.VAlign(VAlign_Center)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.f, 0.f, 0.f, 8.f)
			[
				MakeText(TEXT("OSS TERM PROJECT"), 44, FLinearColor(0.95f, 0.85f, 0.6f))
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.f, 0.f, 0.f, 48.f)
			[
				MakeText(bHasSave ? TEXT("Save found") : TEXT("No save yet"), 14, FLinearColor(0.6f, 0.58f, 0.5f))
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.f, 8.f)
			[
				MakeButton(TEXT("Continue"), bHasSave, [WeakChar]()
				{
					if (WeakChar.IsValid())
					{
						WeakChar->CloseTitleScreen();
					}
				})
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.f, 8.f)
			[
				MakeButton(TEXT("New Game"), true, [WeakChar]()
				{
					if (WeakChar.IsValid())
					{
						WeakChar->StartNewGame();
					}
				})
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.f, 8.f)
			[
				MakeButton(TEXT("Quit"), true, [WeakChar]()
				{
					if (WeakChar.IsValid())
					{
						WeakChar->QuitFromTitle();
					}
				})
			]
		];
}
