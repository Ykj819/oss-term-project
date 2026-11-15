// Boss phase-2 weather: a view effect (unbound post process, optional white frost border on screen) plus falling
// particles (instanced engine shapes around the player). Snow for the wolf, rain for the fishman.
// The owner calls SetWeatherActive(true) when phase 2 starts and SetWeatherActive(false, true) on death / reset.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "BossWeatherComponent.generated.h"

class UPostProcessComponent;
class UInstancedStaticMeshComponent;
class UTexture2D;
class SImage;

UENUM(BlueprintType)
enum class EBossWeather : uint8
{
	Snow,
	Rain
};

UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class UBossWeatherComponent : public UActorComponent
{
	GENERATED_BODY()

public:

	UBossWeatherComponent();

	/** Fades the weather in / out. bInstant = no fade (reset) */
	UFUNCTION(BlueprintCallable, Category="Weather")
	void SetWeatherActive(bool bActive, bool bInstant = false);

	UFUNCTION(BlueprintPure, Category="Weather")
	bool IsWeatherActive() const { return bWeatherOn; }

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	UPROPERTY(EditAnywhere, Category="Weather")
	EBossWeather Weather = EBossWeather::Snow;

	/** Falling particles (snowflakes / raindrops) */
	UPROPERTY(EditAnywhere, Category="Weather", meta = (ClampMin = 0, ClampMax = 4000))
	int32 ParticleCount = 900;

	/** Particles fill a cylinder of this radius / height around the player */
	UPROPERTY(EditAnywhere, Category="Weather", meta = (ClampMin = 100, Units = "cm"))
	float AreaRadius = 1600.f;

	UPROPERTY(EditAnywhere, Category="Weather", meta = (ClampMin = 100, Units = "cm"))
	float AreaHeight = 1100.f;

	/** Seconds to fade in / out */
	UPROPERTY(EditAnywhere, Category="Weather", meta = (ClampMin = 0.1, Units = "s"))
	float FadeTime = 2.f;

	/** How strong the view effect gets (0..1) */
	UPROPERTY(EditAnywhere, Category="Weather", meta = (ClampMin = 0, ClampMax = 1))
	float Intensity = 1.f;

	/** Dark screen edges (post process vignette). Negative = the weather's default (snow 0.3, rain 0.55) */
	UPROPERTY(EditAnywhere, Category="Weather")
	float VignetteIntensity = -1.f;

	/** White frosty border around the screen (snow) */
	UPROPERTY(EditAnywhere, Category="Weather")
	bool bFrostBorder = true;

	/** Frost border opacity at full strength */
	UPROPERTY(EditAnywhere, Category="Weather", meta = (ClampMin = 0, ClampMax = 1))
	float FrostBorderOpacity = 0.85f;

	/** Snowflake brightness: 1 = as bright as white paper in the level's sunlight (they're unlit, so with physical
	 *  auto exposure a plain 1.0 looks dark grey; the sun's lux is read at BeginPlay) */
	UPROPERTY(EditAnywhere, Category="Weather", meta = (ClampMin = 0.05))
	float SnowBrightness = 1.f;

	/** Wind blowing the particles (cm/s, horizontal) */
	UPROPERTY(EditAnywhere, Category="Weather")
	FVector2D Wind = FVector2D(120.f, 60.f);

protected:

	virtual void BeginPlay() override;

	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UPROPERTY(Transient)
	TObjectPtr<UPostProcessComponent> PostProcess;

	UPROPERTY(Transient)
	TObjectPtr<UInstancedStaticMeshComponent> Particles;

	UPROPERTY(Transient)
	TObjectPtr<UTexture2D> FrostTexture;

	TSharedPtr<SImage> FrostImage;
	TSharedPtr<struct FSlateBrush> FrostBrush;

	bool bWeatherOn = false;
	float Weight = 0.f;

	struct FDrop
	{
		FVector Position;
		FVector Velocity;
		float Phase;
		float Size;
	};
	TArray<FDrop> Drops;

	void SetupPostProcess();
	void SetupParticles();
	void ShowFrost(bool bShow);
	void BuildFrostTexture();

	FVector AreaCenter() const;
	void RespawnDrop(FDrop& Drop, const FVector& Center, bool bAnywhere) const;
	void UpdateParticles(float DeltaTime);
};
