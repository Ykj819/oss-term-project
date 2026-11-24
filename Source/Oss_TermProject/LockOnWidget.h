// Lock-on marker drawn on the screen (UMG). The player character projects the target's lock-on point to the screen every
// frame and moves this widget there. Blueprint child: /Game/UI/WBP_LockOn (made by Tools/create_lockon_widget.py) -
// change the look in its Class Defaults (Marker Texture / Color / Size, pulse), or add an Image named "Marker" in the
// Designer to replace the default ring completely.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LockOnWidget.generated.h"

class UImage;
class UTexture2D;

UCLASS()
class ULockOnWidget : public UUserWidget
{
	GENERATED_BODY()

public:

	ULockOnWidget(const FObjectInitializer& ObjectInitializer);

	/** Centre of the marker in viewport pixels */
	void ShowAt(const FVector2D& ScreenPosition);

	void HideMarker();

	/** Short "pop" when a target is locked or switched */
	void PlayLockPulse();

protected:

	/** Optional Image named "Marker" in the Designer; built in code when the Designer is empty */
	UPROPERTY(BlueprintReadOnly, Category="Lock On", meta = (BindWidgetOptional))
	TObjectPtr<UImage> Marker;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Lock On")
	TObjectPtr<UTexture2D> MarkerTexture;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Lock On")
	FLinearColor MarkerColor = FLinearColor(1.f, 0.3f, 0.7f, 1.f);	// pink

	/** On-screen size (pixels at 1080p) */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Lock On")
	FVector2D MarkerSize = FVector2D(40.f, 40.f);

	/** Scale at the start of the lock pulse, shrinking back to 1 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Lock On", meta = (ClampMin = 1))
	float PulseScale = 1.8f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Lock On", meta = (ClampMin = 0.01, Units = "s"))
	float PulseTime = 0.2f;

	/** Gentle breathing while locked (fraction of the size) */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Lock On", meta = (ClampMin = 0))
	float BreatheAmount = 0.06f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Lock On", meta = (ClampMin = 0))
	float BreatheSpeed = 4.f;

	virtual void NativeOnInitialized() override;

	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

private:

	float PulseAge = 100.f;
	float Clock = 0.f;
};
