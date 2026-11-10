// Melee hit detection: while a hit window is open, sweeps spheres along weapon segments (stick, fists...) and damages what they touch once per swing

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "MeleeHitComponent.generated.h"

/** A segment on a component (optionally at a socket/bone) swept as a capsule of spheres */
USTRUCT(BlueprintType)
struct FMeleeHitShape
{
	GENERATED_BODY()

	/** Component the segment is attached to (mesh, weapon...) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	TObjectPtr<USceneComponent> Component;

	/** Socket or bone on Component (None = component origin) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FName Socket;

	/** Segment ends, local to the socket / component (component scale applies) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FVector Start = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FVector End = FVector::ZeroVector;

	/** Sphere radius */
	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	float Radius = 10.f;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FOnMeleeHit, AActor*, HitActor, float, Damage, const FHitResult&, Hit);

UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class UMeleeHitComponent : public UActorComponent
{
	GENERATED_BODY()

public:

	UMeleeHitComponent();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Starts checking Shapes for hits; every actor is damaged at most once until the window ends */
	UFUNCTION(BlueprintCallable, Category="Melee")
	void BeginHitWindow(const TArray<FMeleeHitShape>& Shapes, float Damage);

	/** Stops checking */
	UFUNCTION(BlueprintCallable, Category="Melee")
	void EndHitWindow();

	UFUNCTION(BlueprintPure, Category="Melee")
	bool IsHitWindowOpen() const { return bWindowOpen; }

	/** Fired for every actor hit */
	UPROPERTY(BlueprintAssignable, Category="Melee")
	FOnMeleeHit OnHit;

	/** Actors with any of these tags are never hit (e.g. "Enemy" so enemies don't hit each other) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Melee")
	TArray<FName> IgnoreTags;

	/** Draws the swept spheres */
	UPROPERTY(EditAnywhere, Category="Melee")
	bool bDebugDraw = false;

protected:

	/** Spheres sampled along each segment */
	UPROPERTY(EditAnywhere, Category="Melee", meta = (ClampMin = 1, ClampMax = 16))
	int32 SamplesPerShape = 4;

	bool bWindowOpen = false;
	float WindowDamage = 0.f;
	TArray<FMeleeHitShape> ActiveShapes;

	/** Sample points from the previous frame (sweeps go from there to the current ones so fast swings don't skip targets) */
	TArray<FVector> PreviousPoints;

	UPROPERTY(Transient)
	TSet<TObjectPtr<AActor>> AlreadyHit;

	void GetPoints(TArray<FVector>& OutPoints) const;

	void SweepAndDamage(const TArray<FVector>& From, const TArray<FVector>& To);
};
