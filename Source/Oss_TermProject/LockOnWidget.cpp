// Lock-on marker drawn on the screen (UMG), see LockOnWidget.h

#include "LockOnWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Image.h"
#include "Engine/Texture2D.h"
#include "UObject/ConstructorHelpers.h"

ULockOnWidget::ULockOnWidget(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	static ConstructorHelpers::FObjectFinder<UTexture2D> Ring(TEXT("/Game/UI/T_LockOnRing.T_LockOnRing"));
	if (Ring.Succeeded())
	{
		MarkerTexture = Ring.Object;
	}
}

void ULockOnWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();

	// empty Designer (or a pure C++ instance): one Image as the root
	if (!Marker)
	{
		if (!WidgetTree)
		{
			WidgetTree = NewObject<UWidgetTree>(this, TEXT("WidgetTree"), RF_Transient);
		}
		if (!WidgetTree->RootWidget)
		{
			Marker = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), TEXT("Marker"));
			WidgetTree->RootWidget = Marker;
		}
	}
	if (Marker)
	{
		if (MarkerTexture)
		{
			Marker->SetBrushFromTexture(MarkerTexture);
		}
		Marker->SetDesiredSizeOverride(MarkerSize);
		Marker->SetColorAndOpacity(MarkerColor);
		Marker->SetRenderTransformPivot(FVector2D(0.5f, 0.5f));
	}
	SetVisibility(ESlateVisibility::Collapsed);
}

void ULockOnWidget::ShowAt(const FVector2D& ScreenPosition)
{
	SetAlignmentInViewport(FVector2D(0.5f, 0.5f));
	SetDesiredSizeInViewport(MarkerSize);
	SetPositionInViewport(ScreenPosition, true);
	if (GetVisibility() != ESlateVisibility::HitTestInvisible)
	{
		SetVisibility(ESlateVisibility::HitTestInvisible);
	}
}

void ULockOnWidget::HideMarker()
{
	SetVisibility(ESlateVisibility::Collapsed);
}

void ULockOnWidget::PlayLockPulse()
{
	PulseAge = 0.f;
}

void ULockOnWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);

	Clock += InDeltaTime;
	PulseAge += InDeltaTime;
	float Scale = 1.f + BreatheAmount * FMath::Sin(Clock * BreatheSpeed);
	if (PulseAge < PulseTime)
	{
		const float T = PulseAge / PulseTime;
		Scale *= FMath::Lerp(PulseScale, 1.f, 1.f - (1.f - T) * (1.f - T));	// ease out
	}
	if (Marker)
	{
		Marker->SetRenderScale(FVector2D(Scale, Scale));
	}
}
